"""
Case Memory - Vector-based case retrieval for few-shot learning.

Stores analyzed cases with their outcomes as embeddings, enabling
agents to retrieve similar successful cases as learning examples.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Protocol
from dataclasses import dataclass
import hashlib

from core.schemas.outcome import DealOutcome, DealStatus

logger = logging.getLogger(__name__)


@dataclass
class SimilarCase:
    """A case retrieved for similarity matching."""
    case_id: str
    similarity_score: float
    outcome: DealStatus
    meddic_score: int
    key_insights: List[str]
    winning_strategy: Optional[List[str]]
    industry: Optional[str]
    deal_size: Optional[str]
    summary: str


class VectorStore(Protocol):
    """Protocol for vector database implementations."""

    async def upsert(
        self,
        id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        ...

    async def query(
        self,
        embedding: List[float],
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        ...

    async def delete(self, id: str) -> None:
        ...


class CaseMemory:
    """
    Manages case storage and retrieval using vector embeddings.

    This enables agents to learn from past experiences through
    retrieval-augmented generation (RAG).
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_model: str = "text-embedding-004",
        firestore_client=None,
    ):
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.firestore = firestore_client
        self._embedding_cache: Dict[str, List[float]] = {}

    # =========================================================================
    # Case Storage
    # =========================================================================

    async def store_case(
        self,
        case_id: str,
        case_data: Dict[str, Any],
        outcome: DealOutcome,
    ) -> None:
        """
        Store a completed case with its outcome for future retrieval.

        Cases are embedded and stored when:
        1. Analysis is complete
        2. Outcome is known (closed won/lost)
        """
        # Create searchable text from case
        searchable_text = self._create_searchable_text(case_data, outcome)

        # Generate embedding
        embedding = await self._get_embedding(searchable_text)

        # Prepare metadata for filtering
        metadata = {
            "case_id": case_id,
            "outcome": outcome.actual_outcome.value,
            "meddic_score": outcome.predicted_meddic_score,
            "industry": case_data.get("industry", "unknown"),
            "deal_size_category": self._categorize_deal_size(outcome.actual_deal_value),
            "rep_id": outcome.rep_id,
            "key_objections": case_data.get("objections", []),
            "winning_strategy": outcome.suggestions_followed,
            "summary": searchable_text[:1000],  # First 1000 chars for preview
            "stored_at": datetime.utcnow().isoformat(),
        }

        # Store in vector database
        await self.vector_store.upsert(
            id=case_id,
            embedding=embedding,
            metadata=metadata
        )

        logger.info(f"Stored case {case_id} in memory with outcome {outcome.actual_outcome}")

    def _create_searchable_text(
        self,
        case_data: Dict[str, Any],
        outcome: DealOutcome
    ) -> str:
        """Create a text representation of the case for embedding."""
        parts = []

        # Customer context
        if case_data.get("customerName"):
            parts.append(f"Customer: {case_data['customerName']}")
        if case_data.get("industry"):
            parts.append(f"Industry: {case_data['industry']}")

        # Key analysis points
        analysis = case_data.get("analysis", {})
        agents = analysis.get("agents", {})

        # From buyer analysis
        buyer_data = agents.get("agent2", {}).get("data", {})
        if buyer_data.get("identified_needs"):
            needs = buyer_data["identified_needs"]
            if isinstance(needs, list):
                parts.append(f"Needs: {', '.join(needs[:3])}")

        if buyer_data.get("psychology_hesitations"):
            hesitations = buyer_data["psychology_hesitations"]
            if isinstance(hesitations, list):
                parts.append(f"Objections: {', '.join(hesitations[:3])}")

        # From seller analysis
        seller_data = agents.get("agent3", {}).get("data", {})
        if seller_data.get("coaching_insights"):
            insights = seller_data["coaching_insights"]
            if isinstance(insights, list):
                insight_texts = [i.get("insight", "") for i in insights[:3] if isinstance(i, dict)]
                parts.append(f"Key insights: {', '.join(insight_texts)}")

        # Outcome information
        parts.append(f"MEDDIC Score: {outcome.predicted_meddic_score}")
        parts.append(f"Outcome: {outcome.actual_outcome.value}")

        if outcome.suggestions_followed:
            parts.append(f"Successful strategies: {', '.join(outcome.suggestions_followed[:3])}")

        if outcome.loss_reason:
            parts.append(f"Loss reason: {outcome.loss_reason}")

        return "\n".join(parts)

    def _categorize_deal_size(self, value: Optional[float]) -> str:
        """Categorize deal size for filtering."""
        if value is None:
            return "unknown"
        if value < 10000:
            return "small"
        if value < 50000:
            return "medium"
        if value < 200000:
            return "large"
        return "enterprise"

    # =========================================================================
    # Case Retrieval
    # =========================================================================

    async def retrieve_similar_cases(
        self,
        context: Dict[str, Any],
        outcome_filter: Optional[str] = None,
        industry_filter: Optional[str] = None,
        top_k: int = 5,
    ) -> List[SimilarCase]:
        """
        Retrieve similar cases for few-shot learning.

        Args:
            context: Current case context to match against
            outcome_filter: Filter by outcome (e.g., "closed_won" for success examples)
            industry_filter: Filter by industry for more relevant matches
            top_k: Number of cases to retrieve
        """
        # Create query text from current context
        query_text = self._create_query_text(context)

        # Generate query embedding
        query_embedding = await self._get_embedding(query_text)

        # Build filters
        filters = {}
        if outcome_filter:
            filters["outcome"] = outcome_filter
        if industry_filter:
            filters["industry"] = industry_filter

        # Query vector store
        results = await self.vector_store.query(
            embedding=query_embedding,
            filters=filters if filters else None,
            top_k=top_k
        )

        # Convert to SimilarCase objects
        similar_cases = []
        for result in results:
            metadata = result.get("metadata", {})
            similar_cases.append(SimilarCase(
                case_id=metadata.get("case_id", ""),
                similarity_score=result.get("score", 0.0),
                outcome=DealStatus(metadata.get("outcome", "ongoing")),
                meddic_score=metadata.get("meddic_score", 0),
                key_insights=metadata.get("key_objections", []),
                winning_strategy=metadata.get("winning_strategy"),
                industry=metadata.get("industry"),
                deal_size=metadata.get("deal_size_category"),
                summary=metadata.get("summary", ""),
            ))

        return similar_cases

    def _create_query_text(self, context: Dict[str, Any]) -> str:
        """Create query text from current case context."""
        parts = []

        if context.get("customer_name"):
            parts.append(f"Customer type: {context['customer_name']}")
        if context.get("industry"):
            parts.append(f"Industry: {context['industry']}")
        if context.get("needs"):
            parts.append(f"Needs: {', '.join(context['needs'][:3])}")
        if context.get("objections"):
            parts.append(f"Objections: {', '.join(context['objections'][:3])}")
        if context.get("transcript_summary"):
            parts.append(f"Conversation: {context['transcript_summary'][:500]}")

        return "\n".join(parts) if parts else "sales conversation"

    async def retrieve_success_patterns(
        self,
        context: Dict[str, Any],
        top_k: int = 3
    ) -> List[SimilarCase]:
        """
        Retrieve similar successful cases as positive examples.

        Use this to show agents what worked in similar situations.
        """
        return await self.retrieve_similar_cases(
            context=context,
            outcome_filter="closed_won",
            top_k=top_k
        )

    async def retrieve_failure_patterns(
        self,
        context: Dict[str, Any],
        top_k: int = 2
    ) -> List[SimilarCase]:
        """
        Retrieve similar failed cases as negative examples.

        Use this to show agents what to avoid.
        """
        return await self.retrieve_similar_cases(
            context=context,
            outcome_filter="closed_lost",
            top_k=top_k
        )

    # =========================================================================
    # Rep-Specific Memory
    # =========================================================================

    async def retrieve_rep_history(
        self,
        rep_id: str,
        outcome_filter: Optional[str] = None,
        top_k: int = 10
    ) -> List[SimilarCase]:
        """
        Retrieve a specific rep's past cases for personalization.

        This enables personalized coaching based on individual history.
        """
        # For rep-specific retrieval, we use metadata filtering
        # rather than semantic similarity
        filters = {"rep_id": rep_id}
        if outcome_filter:
            filters["outcome"] = outcome_filter

        # Use a generic query since we're filtering by rep
        dummy_embedding = await self._get_embedding("sales case")

        results = await self.vector_store.query(
            embedding=dummy_embedding,
            filters=filters,
            top_k=top_k
        )

        return [
            SimilarCase(
                case_id=r.get("metadata", {}).get("case_id", ""),
                similarity_score=r.get("score", 0.0),
                outcome=DealStatus(r.get("metadata", {}).get("outcome", "ongoing")),
                meddic_score=r.get("metadata", {}).get("meddic_score", 0),
                key_insights=r.get("metadata", {}).get("key_objections", []),
                winning_strategy=r.get("metadata", {}).get("winning_strategy"),
                industry=r.get("metadata", {}).get("industry"),
                deal_size=r.get("metadata", {}).get("deal_size_category"),
                summary=r.get("metadata", {}).get("summary", ""),
            )
            for r in results
        ]

    # =========================================================================
    # Example Pool Management
    # =========================================================================

    async def get_best_examples(
        self,
        context: Dict[str, Any],
        n_positive: int = 2,
        n_negative: int = 1
    ) -> Dict[str, List[SimilarCase]]:
        """
        Get the best examples for few-shot prompting.

        Returns a mix of successful and failed cases for balanced learning.
        """
        positive = await self.retrieve_success_patterns(context, n_positive)
        negative = await self.retrieve_failure_patterns(context, n_negative)

        return {
            "positive_examples": positive,
            "negative_examples": negative
        }

    def format_examples_for_prompt(
        self,
        examples: Dict[str, List[SimilarCase]]
    ) -> str:
        """Format retrieved examples for injection into prompts."""
        lines = []

        if examples.get("positive_examples"):
            lines.append("## Similar Successful Cases")
            for i, case in enumerate(examples["positive_examples"], 1):
                lines.append(f"\n### Success Example {i}")
                lines.append(f"- MEDDIC Score: {case.meddic_score}")
                lines.append(f"- Outcome: {case.outcome.value}")
                if case.winning_strategy:
                    lines.append(f"- What worked: {', '.join(case.winning_strategy)}")
                lines.append(f"- Summary: {case.summary[:300]}...")

        if examples.get("negative_examples"):
            lines.append("\n## Cases to Learn From (What to Avoid)")
            for i, case in enumerate(examples["negative_examples"], 1):
                lines.append(f"\n### Lesson {i}")
                lines.append(f"- MEDDIC Score: {case.meddic_score}")
                if case.key_insights:
                    lines.append(f"- Key issues: {', '.join(case.key_insights)}")
                lines.append(f"- Summary: {case.summary[:200]}...")

        return "\n".join(lines)

    # =========================================================================
    # Embedding Generation
    # =========================================================================

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using the configured model."""
        # Check cache first
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        # Generate embedding
        # In production, this would call the embedding API
        embedding = await self._generate_embedding(text)

        # Cache the result
        self._embedding_cache[cache_key] = embedding

        return embedding

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using the embedding model.

        This is a placeholder - implement with actual API call.
        """
        # TODO: Implement with actual embedding API
        # For Vertex AI:
        # from vertexai.language_models import TextEmbeddingModel
        # model = TextEmbeddingModel.from_pretrained(self.embedding_model)
        # embeddings = model.get_embeddings([text])
        # return embeddings[0].values

        # Placeholder: return dummy embedding
        import random
        return [random.random() for _ in range(768)]

    # =========================================================================
    # Maintenance
    # =========================================================================

    async def cleanup_old_cases(self, days: int = 365) -> int:
        """Remove cases older than specified days."""
        # Implementation depends on vector store capabilities
        logger.info(f"Cleanup of cases older than {days} days requested")
        return 0

    async def rebuild_index(self) -> None:
        """Rebuild the entire case index from Firestore."""
        if not self.firestore:
            logger.warning("No Firestore client, cannot rebuild index")
            return

        # Get all cases with outcomes
        cases = self.firestore.collection("cases").stream()
        outcomes = {
            doc.id: DealOutcome(**doc.to_dict())
            for doc in self.firestore.collection("outcomes").stream()
        }

        count = 0
        for case_doc in cases:
            case_id = case_doc.id
            if case_id in outcomes:
                await self.store_case(
                    case_id=case_id,
                    case_data=case_doc.to_dict(),
                    outcome=outcomes[case_id]
                )
                count += 1

        logger.info(f"Rebuilt index with {count} cases")
