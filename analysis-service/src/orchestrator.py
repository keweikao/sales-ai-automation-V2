"""
Multi-Agent Orchestrator for Sales AI Automation System (V3 - State-Based Agentic Flow).

This orchestrator implements a state-based dynamic flow with:
- Shared AnalysisState object
- Self-Correction (Reflexion) for quality assurance
- Conditional Triggering for cost optimization

Architecture:
  - Phase 1: Agent 1 (Context) + Agent 2 (Buyer) [Parallel]
  - Phase 2: Quality Loop - Refine Agent 2 if needed (Max 2 retries)
  - Phase 3: Agent 4 (Competitor) - Conditional execution if competitors detected
  - Phase 4: Agent 3 (Seller/Coach) - Synthesis with all available data

Usage:
    orchestrator = MultiAgentOrchestrator()
    results = await orchestrator.analyze_transcript(
        case_id="CASE123",
        transcript_segments=[...],
    )
"""

from __future__ import annotations

from google.cloud import firestore

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Awaitable, Tuple

from .agents.agent1_context import ContextAgent
from .agents.agent2_buyer import BuyerAgent
from .agents.agent3_seller import SellerAgent
from .agents.agent4_summary import SummaryAgent
from .agents.agent6_crm_extractor import CRMExtractorAgent

logger = logging.getLogger(__name__)


from .models import (
    AgentResult,
    AnalysisResult,
    RetryableError,
    NonRetryableError,
    InsufficientDataError,
)
from .filesystem_memory import FileSystemMemory
from .user_preference_memory import UserPreferenceMemory

# P1 Fix: Resilience utilities
try:
    from .resilience import atomic_update, atomic_read_update
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False


from .agents.agent5_coach import CoachAgent, CoachAlert
import os

# =============================================================================
# Shared State Object
# =============================================================================

@dataclass
class AnalysisState:
    """
    Shared state object that flows through the entire analysis pipeline.
    This replaces scattered variable passing with a single state container.
    """
    case_id: str
    transcript: List[Dict[str, Any]]
    
    # Demo Meta (from Slack Modal)
    demo_meta: Optional[Dict[str, Any]] = None
    
    # Agent Outputs
    context_data: Optional[Dict] = None     # From Agent 1
    buyer_data: Optional[Dict] = None       # From Agent 2
    competitor_data: Optional[Dict] = None  # From Agent 4 (Competitor)
    seller_data: Optional[Dict] = None      # From Agent 3
    summary_data: Optional[Dict] = None     # From Agent 4 (Summary - kept for backwards compat)
    
    # Coach Output
    coach_alert: Optional[CoachAlert] = None
    manager_alert: Optional[Any] = None # ManagerAlert
    
    # Metadata for Flow Control
    feedback_history: List[str] = field(default_factory=list)
    detected_intent: str = "sales_pitch"  # Default fixed for sales scenarios
    quality_checks: Dict[str, bool] = field(default_factory=dict)
    
    # Refinement tracking
    buyer_refinement_count: int = 0
    max_refinements: int = 2
    
    # Competitor detection
    competitors_detected: bool = False
    competitor_keywords_found: List[str] = field(default_factory=list)


# =============================================================================
# Competitor Keywords for Detection
# =============================================================================

COMPETITOR_KEYWORDS = [
    # General competitor terms
    "競爭對手", "對手", "其他廠商", "別家", "其他家",
    # Specific competitor brands (POS/Restaurant industry)
    "結帳快手", "海底撈", "foodpanda", "uber eats", "inline",
    "eztable", "候位", "訂位系統", "pos系統", "收銀機",
    # Comparison terms
    "比較", "相比", "對比", "跟別人", "其他選擇", "替代方案",
]


class MultiAgentOrchestrator:
    """
    Orchestrates execution of the Sales AI Agents with state-based flow.
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        temperature: float = 0.2,
        min_success_threshold: int = 3,
        enable_agent_retry: bool = True,
        agent_retry_attempts: int = 2,
        model_config: Optional[Dict[str, str]] = None,
        db_client: Optional[firestore.Client] = None,
        resume_mode: bool = False,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.enable_agent_retry = enable_agent_retry
        self.agent_retry_attempts = agent_retry_attempts
        self.model_config = model_config or {}
        self.db = db_client
        self.resume_mode = resume_mode
        self.memory = FileSystemMemory() if resume_mode else None
        self.preference_memory = UserPreferenceMemory()

        # Initialize agents lazily
        self._agents: Optional[Dict[str, Any]] = None

    def _ensure_agents(self) -> Dict[str, Any]:
        """Lazy initialization of agent instances."""
        if self._agents is None:
            logger.info("Initializing Agent 1-4 instances (V3 State-Based Architecture)...")
            self._agents = {
                "agent1": ContextAgent(
                    model_name=self.model_config.get("agent1", self.model_name),
                    temperature=self.temperature
                ),
                "agent2": BuyerAgent(
                    model_name=self.model_config.get("agent2", self.model_name),
                    temperature=self.temperature
                ),
                "agent3": SellerAgent(
                    model_name=self.model_config.get("agent3", self.model_name),
                    temperature=self.temperature
                ),
                "agent4": SummaryAgent(
                    model_name=self.model_config.get("agent4", self.model_name),
                    temperature=self.temperature
                ),
                "agent6": CRMExtractorAgent(
                    model_name=self.model_config.get("agent6", self.model_name),
                    temperature=self.temperature
                ),
            }
            logger.info(f"Initialized {len(self._agents)} agents successfully")
        return self._agents

    # =========================================================================
    # Quality Evaluation Functions
    # =========================================================================

    def _evaluate_buyer_quality(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Evaluate the quality of Agent 2 (Buyer) output.
        
        Returns:
            Tuple of (is_acceptable, feedback_message)
        """
        if not data:
            return False, "分析結果為空，請重新分析對話內容。"
        
        issues = []
        
        # Rule 1: Check for identified needs
        needs = data.get("identifiedNeeds", [])
        if not needs:
            issues.append("未識別到任何客戶需求 (identifiedNeeds 為空)")
        elif len(needs) < 2:
            issues.append("識別到的需求太少，請更仔細分析客戶的需求點")
        
        # Rule 2: Check for pain points (from psychology section)
        psychology = data.get("psychology", {})
        hesitations = psychology.get("hesitations", [])
        if not hesitations:
            issues.append("未識別到任何客戶疑慮或痛點 (hesitations 為空)")
        
        # Rule 3: Check MEDDIC pain
        meddic = data.get("meddic", {})
        pain = meddic.get("pain", "")
        if not pain or len(pain) < 10:
            issues.append("MEDDIC 痛點描述過於簡短或為空，請深入分析客戶的核心問題")
        
        # Rule 4: Check trust score validity
        trust_score = psychology.get("trustScore", -1)
        if trust_score < 0 or trust_score > 100:
            issues.append("信任分數無效，請重新評估")
        
        if issues:
            feedback = "你上次的分析結果有以下問題需要修正：\n" + "\n".join(f"- {i}" for i in issues)
            feedback += "\n\n請專注於對話內容中客戶表達的需求、疑慮和痛點，重新進行更深入的分析。"
            return False, feedback
        
        return True, ""

    def _detect_competitors(self, state: AnalysisState) -> bool:
        """
        Detect if competitors are mentioned in the transcript or buyer analysis.
        
        Uses keyword matching for efficiency (no LLM call needed).
        """
        # Check transcript text
        transcript_text = ""
        for seg in state.transcript:
            text = seg.get("text", "")
            transcript_text += text.lower() + " "
        
        # Check for keywords
        found_keywords = []
        for keyword in COMPETITOR_KEYWORDS:
            if keyword.lower() in transcript_text:
                found_keywords.append(keyword)
        
        # Also check buyer data if available
        if state.buyer_data:
            meddic = state.buyer_data.get("meddic", {})
            competition = meddic.get("competition", "")
            if competition and len(competition) > 5:
                found_keywords.append(f"MEDDIC competition: {competition[:50]}")
        
        state.competitor_keywords_found = found_keywords
        state.competitors_detected = len(found_keywords) > 0
        
        if state.competitors_detected:
            logger.info(f"Competitors detected: {found_keywords[:5]}")
        else:
            logger.info("No competitors detected, will skip Agent 4 (Competitor)")
        
        return state.competitors_detected

    # =========================================================================
    # Persistence Functions
    # =========================================================================

    def _persist_agent_result(
        self, 
        case_id: str, 
        agent_id: str, 
        result: AgentResult,
        extra_fields: Optional[Dict[str, Any]] = None
    ) -> None:
        """Generic method to persist agent results to Firestore."""
        if not self.db or not result.success or not result.data:
            return

        try:
            case_ref = self.db.collection('cases').document(case_id)
            
            agent_data = {
                'status': 'success',
                'duration': result.duration,
                'retryCount': result.retry_count,
                'data': result.data,
                'updatedAt': firestore.SERVER_TIMESTAMP,
            }
            
            update_data = {
                'analysis': {
                    'agents': {agent_id: agent_data},
                    'updatedAt': firestore.SERVER_TIMESTAMP,
                }
            }
            
            if extra_fields:
                update_data['analysis'].update(extra_fields)
            
            case_ref.set(update_data, merge=True)
            logger.info(f"{agent_id} results persisted for case {case_id}")
        except Exception as exc:
            logger.error(f"Failed to persist {agent_id} results: {exc}", exc_info=True)

    def _persist_summary_results(self, case_id: str, result: AgentResult) -> None:
        """Persist Agent 4 (Summary) results with customerSummary field.
        
        Also replaces placeholders like [客戶名稱] with actual values.
        """
        if not self.db or not result.success or not result.data:
            return

        try:
            case_ref = self.db.collection('cases').document(case_id)
            
            # Fetch case data to get customer and sales rep names
            case_doc = case_ref.get()
            customer_name = "客戶"
            sales_rep_name = "業務代表"
            
            if case_doc.exists:
                case_data = case_doc.to_dict() or {}
                customer_name = case_data.get('customerName') or "客戶"
                sales_rep_name = case_data.get('salesRepName') or case_data.get('uploadedByName') or "業務代表"
            
            # Replace placeholders in summary data
            logger.info(f"Replacing placeholders for case {case_id}: customer='{customer_name}', salesRep='{sales_rep_name}'")
            
            # DEBUG: Check if placeholders exist in original data
            original_md = result.data.get('markdown', '') if isinstance(result.data, dict) else ''
            has_placeholder = '[客戶名稱]' in original_md or '[業務姓名]' in original_md
            logger.info(f"DEBUG: Original markdown has placeholders: {has_placeholder}")
            
            summary_data = self._replace_placeholders(
                result.data, 
                customer_name=customer_name,
                sales_rep_name=sales_rep_name
            )
            
            # DEBUG: Check if placeholders were replaced
            replaced_md = summary_data.get('markdown', '') if isinstance(summary_data, dict) else ''
            still_has_placeholder = '[客戶名稱]' in replaced_md or '[業務姓名]' in replaced_md
            logger.info(f"DEBUG: Replaced markdown still has placeholders: {still_has_placeholder}")
            
            update_data = {
                'analysis': {
                    'customerSummary': summary_data,
                    'agents': {
                        'agent4': {
                            'status': 'success',
                            'duration': result.duration,
                            'retryCount': result.retry_count,
                            'data': summary_data,
                            'updatedAt': firestore.SERVER_TIMESTAMP,
                        }
                    },
                    'updatedAt': firestore.SERVER_TIMESTAMP,
                }
            }
            
            # P1 Fix: Use atomic transaction for data consistency
            if RESILIENCE_AVAILABLE:
                success = atomic_update(self.db, case_ref, update_data)
                if success:
                    logger.info(f"Agent 4 (Summary) results persisted atomically for case {case_id}")
                else:
                    # Fallback to regular update
                    case_ref.set(update_data, merge=True)
                    logger.warning(f"Agent 4 atomic update failed, used fallback for case {case_id}")
            else:
                case_ref.set(update_data, merge=True)
                logger.info(f"Agent 4 (Summary) results persisted for case {case_id} with placeholders replaced")
        except Exception as exc:
            logger.error(f"Failed to persist Agent 4 results: {exc}", exc_info=True)

    def _replace_placeholders(
        self, 
        data: Dict[str, Any], 
        customer_name: str,
        sales_rep_name: str
    ) -> Dict[str, Any]:
        """Replace placeholders in summary data with actual values."""
        import copy
        import re
        
        result = copy.deepcopy(data)
        
        # Define placeholder patterns and their replacements
        replacements = {
            r'\[店名\]': customer_name,
            r'\[客戶名稱\]': customer_name,
            r'\[客戶姓名\]': customer_name,
            r'\[業務名稱\]': sales_rep_name,
            r'\[業務姓名\]': sales_rep_name,
            r'\[Sales Rep Name\]': sales_rep_name,
            r'\[Customer Name\]': customer_name,
        }
        
        def replace_in_string(text: str) -> str:
            if not isinstance(text, str):
                return text
            for pattern, replacement in replacements.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            return text
        
        def replace_recursive(obj):
            if isinstance(obj, str):
                return replace_in_string(obj)
            elif isinstance(obj, dict):
                return {k: replace_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_recursive(item) for item in obj]
            else:
                return obj
        
        return replace_recursive(result)

    # =========================================================================
    # Agent Runners
    # =========================================================================

    async def _run_agent(
        self,
        agent,
        agent_id: str,
        run_func: Callable,
    ) -> AgentResult:
        """Generic agent runner with timing."""
        start = time.time()
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, run_func)
            return AgentResult(
                agent_id,
                True,
                data=response.data,
                duration=time.time() - start,
                metadata={'report': response.report}
            )
        except Exception as e:
            logger.error(f"{agent_id} failed: {e}", exc_info=True)
            return AgentResult(agent_id, False, error=str(e), duration=time.time() - start)

    async def _run_agent_with_retry(
        self,
        case_id: str,
        agent_id: str,
        run_func: Callable,
    ) -> AgentResult:
        """Run agent with retry logic."""
        max_attempts = self.agent_retry_attempts + 1 if self.enable_agent_retry else 1
        last_error = None

        for attempt in range(max_attempts):
            try:
                start = time.time()
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, run_func)
                result = AgentResult(
                    agent_id,
                    True,
                    data=response.data,
                    duration=time.time() - start,
                    metadata={'report': response.report},
                    retry_count=attempt
                )
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"{agent_id} failed attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 * (attempt + 1))

        return AgentResult(
            agent_id=agent_id,
            success=False,
            error=str(last_error),
            retry_count=max_attempts
        )

    # =========================================================================
    # Refinement Logic
    # =========================================================================

    async def _refine_buyer_analysis(
        self,
        state: AnalysisState,
        agent: BuyerAgent,
        feedback: str
    ) -> AgentResult:
        """
        Refine Agent 2 (Buyer) analysis using the refine() method.
        """
        logger.info(f"Refining Agent 2 analysis (attempt {state.buyer_refinement_count + 1})")
        state.feedback_history.append(feedback)
        
        start = time.time()
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: agent.refine(
                    transcript_segments=state.transcript,
                    previous_result=state.buyer_data or {},
                    feedback=feedback,
                )
            )
            state.buyer_refinement_count += 1
            return AgentResult(
                "agent2",
                True,
                data=response.data,
                duration=time.time() - start,
                metadata={'report': response.report, 'refined': True}
            )
        except Exception as e:
            logger.error(f"Agent 2 refinement failed: {e}", exc_info=True)
            return AgentResult("agent2", False, error=str(e), duration=time.time() - start)

    # =========================================================================
    # Main Analysis Pipeline
    # =========================================================================

    async def analyze_transcript(
        self,
        case_id: str,
        transcript_segments: List[Dict[str, Any]],
        speaker_statistics: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        Execute the State-Based Agentic Pipeline.
        
        Flow:
        1. Phase 1: Agent 1 (Context) + Agent 2 (Buyer) in parallel
        2. Phase 2: Quality Loop - Refine Agent 2 if needed
        3. Phase 3: Agent 4 (Competitor) - Conditional
        4. Phase 4: Agent 3 (Seller/Coach) - Synthesis
        5. Phase 5: Agent 4 (Summary) - Generate customer summary
        """
        logger.info(f"Starting V3 (State-Based) analysis for case {case_id}")
        start_time = time.time()
        
        # Load demo_meta from Firestore if available
        demo_meta = None
        if self.db:
            try:
                case_doc = self.db.collection('cases').document(case_id).get()
                if case_doc.exists:
                    case_data = case_doc.to_dict() or {}
                    demo_meta = case_data.get('demoMeta')
                    if demo_meta:
                        logger.info(f"Loaded demo_meta for case {case_id}: {demo_meta}")
            except Exception as e:
                logger.warning(f"Failed to load demo_meta for case {case_id}: {e}")
        
        # Initialize shared state
        state = AnalysisState(
            case_id=case_id,
            transcript=transcript_segments,
            demo_meta=demo_meta
        )
        
        agents = self._ensure_agents()
        agent_results = {}

        # =====================================================================
        # Phase 1: Base Analysis (Context + Buyer in parallel)
        # =====================================================================
        logger.info("Phase 1: Agent 1 (Context) + Agent 2 (Buyer) [Parallel]")
        
        # Capture demo_meta for lambda closure
        _demo_meta = state.demo_meta
        
        result_a1, result_a2 = await asyncio.gather(
            self._run_agent_with_retry(
                case_id, "agent1",
                lambda: agents['agent1'].analyze(
                    transcript_segments=transcript_segments,
                    demo_meta=_demo_meta
                )
            ),
            self._run_agent_with_retry(
                case_id, "agent2",
                lambda: agents['agent2'].analyze(
                    transcript_segments=transcript_segments,
                    context_insights={}  # Will be empty for first pass
                )
            )
        )
        
        agent_results['agent1'] = result_a1
        agent_results['agent2'] = result_a2
        
        # Update state
        if result_a1.success:
            state.context_data = result_a1.data
            self._persist_agent_result(case_id, 'agent1', result_a1)
        else:
            logger.error("Agent 1 failed. Continuing with limited context.")
        
        if result_a2.success:
            state.buyer_data = result_a2.data
        else:
            logger.warning("Agent 2 failed initial analysis.")

        # =====================================================================
        # Phase 2: Quality Loop (Refine Agent 2 if needed)
        # =====================================================================
        logger.info("Phase 2: Quality Loop for Agent 2 (Buyer)")
        
        while result_a2.success and state.buyer_refinement_count < state.max_refinements:
            is_acceptable, feedback = self._evaluate_buyer_quality(state.buyer_data or {})
            
            if is_acceptable:
                state.quality_checks['buyer'] = True
                logger.info("Agent 2 quality check passed!")
                break
            
            logger.info(f"Agent 2 quality check failed. Triggering refinement...")
            result_a2 = await self._refine_buyer_analysis(state, agents['agent2'], feedback)
            
            if result_a2.success:
                state.buyer_data = result_a2.data
                agent_results['agent2'] = result_a2
            else:
                logger.warning("Agent 2 refinement failed, using previous result")
                break
        
        # Persist final Agent 2 result
        if result_a2.success:
            self._persist_agent_result(case_id, 'agent2', result_a2)

        # =====================================================================
        # Phase 3: Conditional Competitor Analysis
        # =====================================================================
        logger.info("Phase 3: Conditional Competitor Detection")
        
        # Check if competitors are mentioned
        has_competitors = self._detect_competitors(state)
        
        if has_competitors:
            logger.info("Competitors detected! Running Agent 4 (Competitor Analysis)...")
            # Note: For now we reuse Agent 4 for competitor analysis
            # In a full implementation, you'd have a dedicated competitor agent
            # state.competitor_data = ... (if you have a separate competitor agent)
        else:
            logger.info("No competitors detected. Skipping competitor analysis to save tokens.")
            state.competitor_data = None

        # =====================================================================
        # Phase 4: Synthesis (Agent 3 - Seller/Coach)
        # =====================================================================
        logger.info("Phase 4: Agent 3 (Seller/Coach) - Synthesis")
        
        result_a3 = await self._run_agent_with_retry(
            case_id, "agent3",
            lambda: agents['agent3'].analyze(
                transcript_segments=transcript_segments,
                context_insights=state.context_data or {},
                buyer_insights=state.buyer_data or {}
            )
        )
        agent_results['agent3'] = result_a3
        
        if result_a3.success:
            state.seller_data = result_a3.data
            self._persist_agent_result(case_id, 'agent3', result_a3)
        else:
            logger.warning("Agent 3 failed. Sales coaching unavailable.")

        # =====================================================================
        # Phase 5: Summary (Agent 4 - Summary Generation)
        # =====================================================================
        logger.info("Phase 5: Agent 4 (Summary)")
        
        result_a4 = await self._run_agent_with_retry(
            case_id, "agent4",
            lambda: agents['agent4'].analyze(
                transcript_segments=transcript_segments,
                context_insights=state.context_data or {}
            )
        )
        agent_results['agent4'] = result_a4
        
        if result_a4.success:
            state.summary_data = result_a4.data
            self._persist_summary_results(case_id, result_a4)

        # =====================================================================
        # Phase 6: CRM Extraction (Agent 6 - Salesforce 欄位擷取)
        # =====================================================================
        logger.info("Phase 6: Agent 6 (CRM Extractor)")
        
        result_a6 = await self._run_agent_with_retry(
            case_id, "agent6",
            lambda: agents['agent6'].extract(
                transcript_segments=transcript_segments,
                context_insights=state.context_data or {},
                buyer_insights=state.buyer_data or {},
                seller_insights=state.seller_data or {}
            )
        )
        agent_results['agent6'] = result_a6
        
        if result_a6.success:
            self._persist_agent_result(case_id, 'agent6', result_a6)
            # Trigger CRM update asynchronously
            self._trigger_crm_update(case_id, result_a6.data)
        else:
            logger.warning("Agent 6 (CRM Extractor) failed. Salesforce update skipped.")

        # =====================================================================
        # Phase 6: Agent 5 (Sales Coach) - Evaluate
        # =====================================================================
        logger.info("Phase 6: Agent 5 (Sales Coach) - Evaluate")
        
        try:
            # Get case data for rep info
            case_data = {}
            if self.db:
                case_doc = self.db.collection('cases').document(case_id).get()
                if case_doc.exists:
                    case_data = case_doc.to_dict() or {}
            
            coach_agent = CoachAgent(
                db_client=self.db, 
                gemini_api_key=os.environ.get("GEMINI_API_KEY")
            )
            
            # Evaluate if alert is needed
            coach_alert = coach_agent.evaluate(
                case_id=case_id,
                rep_id=case_data.get("uploadedBy", ""),
                rep_name=case_data.get("uploadedByName", "") or case_data.get("salesRepName", ""),
                store_name=case_data.get("customerName", ""),
                context_data=state.context_data or {},
                buyer_data=state.buyer_data or {},
                seller_data=state.seller_data or {},
            )
            
            state.coach_alert = coach_alert
            
            # If alert triggered, save it
            if coach_alert:
                logger.info(f"Coach Alert Triggered: {coach_alert.alert_type}")
                
                # Get slack channel/ts from notification field if available
                notification = case_data.get("notification", {})
                slack_channel = notification.get("slackChannelId", "")
                slack_ts = notification.get("slackThreadTs", "")
                
                coach_agent.save_alert(coach_alert, slack_channel, slack_ts)
            else:
                logger.info("No Coach Alert triggered for this case.")

            # Manager Alert (Phase 5)
            # Check for anomalies like consecutive low scores
            rep_id = case_data.get("uploadedBy", "")
            current_score = 0
            if state.seller_data:
                current_score = state.seller_data.get("progress_score", 0)
                
            manager_alert = coach_agent.evaluate_manager_alert(
                case_id=case_id,
                rep_id=rep_id,
                current_score=current_score
            )
            state.manager_alert = manager_alert
            
            if manager_alert:
                coach_agent.save_manager_alert(manager_alert)
                logger.info(f"Manager Alert Triggered: {manager_alert.alert_type}")
                
        except Exception as e:
            logger.error(f"Agent 5 (Coach) execution failed: {e}", exc_info=True)

        # =====================================================================
        # Final Status
        # =====================================================================
        success = (
            result_a1.success and 
            result_a2.success and 
            result_a3.success
        )
        total_duration = time.time() - start_time
        
        logger.info(f"Analysis V3 complete. Success: {success}. Duration: {total_duration:.2f}s")
        logger.info(f"Quality checks: {state.quality_checks}")
        logger.info(f"Buyer refinements: {state.buyer_refinement_count}")
        logger.info(f"Competitors detected: {state.competitors_detected}")

        return AnalysisResult(
            case_id=case_id,
            success=success,
            agent_results=agent_results,
            total_duration=total_duration,
            coach_alert=state.coach_alert,
            manager_alert=state.manager_alert
        )

    def _trigger_crm_update(self, case_id: str, agent6_data: Dict[str, Any]) -> None:
        """
        Trigger CRM service to update Salesforce.
        
        This is a fire-and-forget async call to crm-service.
        """
        import os
        import requests
        
        crm_service_url = os.environ.get("CRM_SERVICE_URL")
        if not crm_service_url:
            logger.info("CRM_SERVICE_URL not configured, skipping Salesforce update")
            return
        
        try:
            # Get customer_id from case
            customer_id = None
            if self.db:
                case_doc = self.db.collection('cases').document(case_id).get()
                if case_doc.exists:
                    case_data = case_doc.to_dict() or {}
                    customer = case_data.get('customer', {})
                    customer_id = customer.get('id')
            
            if not customer_id:
                logger.warning(f"No customer_id found for case {case_id}, skipping CRM update")
                return
            
            # Prepare update payload
            stage_name = agent6_data.get('stage_name')
            payload = {
                "customerId": customer_id,
                "stageName": stage_name or "Needs Analysis",
            }
            
            # Call update-status endpoint
            response = requests.post(
                f"{crm_service_url}/update-status",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully triggered CRM update for case {case_id}")
            else:
                logger.warning(f"CRM update failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to trigger CRM update for case {case_id}: {e}")

