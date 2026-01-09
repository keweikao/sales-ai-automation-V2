"""
Outcome Tracker - Syncs deal outcomes from CRM for learning.

This service bridges the gap between agent predictions and actual results,
enabling the learning loop that makes agents truly adaptive.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from core.schemas.outcome import (
    DealOutcome,
    DealStatus,
    OutcomePattern,
)

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """
    Tracks and syncs deal outcomes from Salesforce.

    The outcome tracker is the foundation of the learning system.
    Without knowing what actually happened, agents cannot improve.
    """

    def __init__(
        self,
        firestore_client,
        salesforce_client,
        bigquery_client=None,
    ):
        self.firestore = firestore_client
        self.salesforce = salesforce_client
        self.bigquery = bigquery_client

    async def sync_outcomes(self, lookback_days: int = 30) -> List[DealOutcome]:
        """
        Sync deal outcomes from Salesforce for recently analyzed cases.

        This should run on a schedule (e.g., daily) to keep outcomes updated.
        """
        synced_outcomes = []

        # Get cases analyzed in the lookback period
        cases = await self._get_analyzed_cases(lookback_days)
        logger.info(f"Found {len(cases)} cases to sync outcomes for")

        for case in cases:
            try:
                outcome = await self._sync_single_outcome(case)
                if outcome:
                    synced_outcomes.append(outcome)
            except Exception as e:
                logger.error(f"Failed to sync outcome for case {case['id']}: {e}")

        # Store aggregated outcomes in BigQuery for analysis
        if self.bigquery and synced_outcomes:
            await self._store_outcomes_bigquery(synced_outcomes)

        logger.info(f"Synced {len(synced_outcomes)} outcomes")
        return synced_outcomes

    async def _get_analyzed_cases(self, lookback_days: int) -> List[Dict]:
        """Get cases that have been analyzed but may need outcome updates."""
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)

        cases_ref = self.firestore.collection("cases")
        query = cases_ref.where("status", "==", "completed")
        query = query.where("completedAt", ">=", cutoff)

        docs = query.stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]

    async def _sync_single_outcome(self, case: Dict) -> Optional[DealOutcome]:
        """Sync outcome for a single case from Salesforce."""
        # Get the Salesforce opportunity ID
        sf_opportunity_id = case.get("salesforce_opportunity_id")
        if not sf_opportunity_id:
            # Try to find by customer name/account
            sf_opportunity_id = await self._find_opportunity(case)

        if not sf_opportunity_id:
            logger.debug(f"No Salesforce opportunity found for case {case['id']}")
            return None

        # Fetch current opportunity status from Salesforce
        opportunity = await self.salesforce.get_opportunity(sf_opportunity_id)
        if not opportunity:
            return None

        # Extract agent predictions from the case
        analysis = case.get("analysis", {})
        agent_data = analysis.get("agents", {})

        predicted_score = self._extract_meddic_score(agent_data)
        predicted_qual = self._extract_qualification(agent_data)
        suggestions = self._extract_suggestions(agent_data)

        # Map Salesforce stage to our status
        actual_status = self._map_sf_stage(opportunity.get("StageName", ""))

        # Create outcome record
        outcome = DealOutcome(
            case_id=case["id"],
            salesforce_opportunity_id=sf_opportunity_id,
            predicted_meddic_score=predicted_score,
            predicted_qualification=predicted_qual,
            predicted_close_probability=predicted_score / 100.0,
            predicted_close_date=case.get("predicted_close_date"),
            coaching_suggestions_given=suggestions,
            actual_outcome=actual_status,
            actual_close_date=self._parse_date(opportunity.get("CloseDate")),
            actual_deal_value=opportunity.get("Amount"),
            loss_reason=opportunity.get("Loss_Reason__c") if actual_status == DealStatus.CLOSED_LOST else None,
            rep_id=case.get("uploadedBy", ""),
            rep_name=case.get("uploadedByName", ""),
            synced_from_crm_at=datetime.utcnow(),
        )

        # Calculate prediction accuracy
        outcome.prediction_error = self._calculate_prediction_error(outcome)

        # Store in Firestore
        await self._store_outcome(outcome)

        return outcome

    async def _find_opportunity(self, case: Dict) -> Optional[str]:
        """Try to find matching Salesforce opportunity by customer info."""
        customer_name = case.get("customerName", "")
        if not customer_name:
            return None

        # Search in Salesforce
        opportunities = await self.salesforce.search_opportunities(
            account_name=customer_name,
            created_after=case.get("createdAt")
        )

        if opportunities:
            # Return the most likely match
            return opportunities[0].get("Id")

        return None

    def _map_sf_stage(self, stage: str) -> DealStatus:
        """Map Salesforce stage to our DealStatus enum."""
        stage_lower = stage.lower()

        if "closed won" in stage_lower or "won" in stage_lower:
            return DealStatus.CLOSED_WON
        elif "closed lost" in stage_lower or "lost" in stage_lower:
            return DealStatus.CLOSED_LOST
        elif "stalled" in stage_lower or "on hold" in stage_lower:
            return DealStatus.STALLED
        elif "nurture" in stage_lower or "qualify" in stage_lower:
            return DealStatus.NURTURING
        else:
            return DealStatus.ONGOING

    def _extract_meddic_score(self, agent_data: Dict) -> int:
        """Extract MEDDIC score from agent analysis."""
        buyer_data = agent_data.get("agent2", {}).get("data", {})
        meddic = buyer_data.get("meddic_score", {})

        if isinstance(meddic, dict):
            return meddic.get("total_score", 50)
        return 50  # Default

    def _extract_qualification(self, agent_data: Dict) -> str:
        """Extract qualification status from agent analysis."""
        buyer_data = agent_data.get("agent2", {}).get("data", {})
        meddic = buyer_data.get("meddic_score", {})

        if isinstance(meddic, dict):
            return meddic.get("qualification_status", "nurture")
        return "nurture"

    def _extract_suggestions(self, agent_data: Dict) -> List[str]:
        """Extract coaching suggestions from agent analysis."""
        seller_data = agent_data.get("agent3", {}).get("data", {})
        suggestions = seller_data.get("coaching_insights", [])

        return [s.get("suggestion", "") for s in suggestions if isinstance(s, dict)]

    def _calculate_prediction_error(self, outcome: DealOutcome) -> float:
        """Calculate how wrong the prediction was."""
        if outcome.actual_outcome == DealStatus.CLOSED_WON:
            # Perfect prediction would be score of 100
            return (100 - outcome.predicted_meddic_score) / 100.0
        elif outcome.actual_outcome == DealStatus.CLOSED_LOST:
            # Perfect prediction would be score of 0
            return outcome.predicted_meddic_score / 100.0
        else:
            return 0.0  # Can't calculate for ongoing deals

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string from Salesforce."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return None

    async def _store_outcome(self, outcome: DealOutcome):
        """Store outcome in Firestore."""
        doc_ref = self.firestore.collection("outcomes").document(outcome.case_id)
        await doc_ref.set(outcome.model_dump())

    async def _store_outcomes_bigquery(self, outcomes: List[DealOutcome]):
        """Store outcomes in BigQuery for analysis."""
        if not self.bigquery:
            return

        rows = [o.model_dump() for o in outcomes]
        await self.bigquery.insert_rows("learning.outcomes", rows)

    # =========================================================================
    # Pattern Discovery
    # =========================================================================

    async def discover_patterns(
        self,
        min_sample_size: int = 10,
        min_confidence: float = 0.7
    ) -> List[OutcomePattern]:
        """
        Analyze outcomes to discover success/failure patterns.

        These patterns can be used to improve agent predictions.
        """
        patterns = []

        # Get all outcomes
        outcomes = await self._get_all_outcomes()

        if len(outcomes) < min_sample_size:
            logger.info(f"Not enough outcomes ({len(outcomes)}) for pattern discovery")
            return patterns

        # Analyze by different dimensions
        patterns.extend(await self._analyze_by_industry(outcomes, min_sample_size, min_confidence))
        patterns.extend(await self._analyze_by_deal_size(outcomes, min_sample_size, min_confidence))
        patterns.extend(await self._analyze_by_rep(outcomes, min_sample_size, min_confidence))
        patterns.extend(await self._analyze_by_meddic_component(outcomes, min_sample_size, min_confidence))

        # Store discovered patterns
        for pattern in patterns:
            await self._store_pattern(pattern)

        return patterns

    async def _get_all_outcomes(self) -> List[DealOutcome]:
        """Get all stored outcomes."""
        docs = self.firestore.collection("outcomes").stream()
        return [DealOutcome(**doc.to_dict()) for doc in docs]

    async def _analyze_by_industry(
        self,
        outcomes: List[DealOutcome],
        min_sample: int,
        min_confidence: float
    ) -> List[OutcomePattern]:
        """Find patterns by industry."""
        # Implementation would group by industry and calculate success rates
        # This is a placeholder for the actual analysis
        return []

    async def _analyze_by_deal_size(
        self,
        outcomes: List[DealOutcome],
        min_sample: int,
        min_confidence: float
    ) -> List[OutcomePattern]:
        """Find patterns by deal size."""
        return []

    async def _analyze_by_rep(
        self,
        outcomes: List[DealOutcome],
        min_sample: int,
        min_confidence: float
    ) -> List[OutcomePattern]:
        """Find patterns by sales rep."""
        return []

    async def _analyze_by_meddic_component(
        self,
        outcomes: List[DealOutcome],
        min_sample: int,
        min_confidence: float
    ) -> List[OutcomePattern]:
        """Find which MEDDIC components best predict outcomes."""
        return []

    async def _store_pattern(self, pattern: OutcomePattern):
        """Store discovered pattern."""
        doc_ref = self.firestore.collection("outcome_patterns").document(pattern.pattern_id)
        await doc_ref.set(pattern.model_dump())
