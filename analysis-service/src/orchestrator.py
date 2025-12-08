"""
Multi-Agent Orchestrator for Sales AI Automation System (V2 - 3+1 Architecture).

Orchestrates the execution of 4 agents:
1. Agent 1: Context (The Scene)
2. Agent 2: Buyer (The Customer & Product)
3. Agent 3: Seller (The Sales Coach)
4. Agent 4: Summary (The Recap - External)

Architecture:
  - Phase 1: Agent 1 (Context)
  - Phase 2: Agent 2 (Buyer) + Agent 4 (Summary) [Parallel]
  - Phase 3: Agent 3 (Seller) [Depends on Agent 2]

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
import copy
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Awaitable

from .agents.agent1_context import ContextAgent
from .agents.agent2_buyer import BuyerAgent
from .agents.agent3_seller import SellerAgent
from .agents.agent4_summary import SummaryAgent

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


class MultiAgentOrchestrator:
    """
    Orchestrates execution of the 3+1 Sales AI Agents.
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.2,
        min_success_threshold: int = 3, # Not strictly used in new flow but kept for compat
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

        # Initialize agents
        self._agents: Optional[Dict[str, Any]] = None

    def _ensure_agents(self) -> Dict[str, Any]:
        """Lazy initialization of agent instances."""
        if self._agents is None:
            logger.info("Initializing Agent 1-4 instances (V2 Architecture)...")
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
            }
            logger.info(f"Initialized {len(self._agents)} agents successfully")
        return self._agents

    def _persist_agent3_results(self, case_id: str, agent3_result: AgentResult) -> None:
        """Persist Agent 3 (Seller/Coach) results to Firestore (replaces old Agent 6)."""
        if not self.db or not agent3_result.success or not agent3_result.data:
            return

        try:
            case_ref = self.db.collection('cases').document(case_id)
            analysis_update: Dict[str, Any] = {}

            # Map new structure to old fields if necessary, or just save as agent3
            # We'll save primarily under 'agents.agent3' but also promote key metrics if needed
            
            agents_section = analysis_update.setdefault('agents', {})
            agents_section['agent3'] = {
                'status': 'success',
                'duration': agent3_result.duration,
                'retryCount': agent3_result.retry_count,
                'data': agent3_result.data,
                'updatedAt': firestore.SERVER_TIMESTAMP,
            }
            analysis_update['updatedAt'] = firestore.SERVER_TIMESTAMP

            case_ref.set({'analysis': analysis_update}, merge=True)
            logger.info("Agent 3 (Seller) results persisted for case %s", case_id)
        except Exception as exc:
            logger.error("Failed to persist Agent 3 results: %s", exc, exc_info=True)

    def _persist_agent4_results(self, case_id: str, agent4_result: AgentResult) -> None:
        """Persist Agent 4 (Summary) results to Firestore (replaces old Agent 7)."""
        if not self.db or not agent4_result.success or not agent4_result.data:
            return

        # Agent 4 output format: { "subject": ..., "summary": ..., "actionItems": ... }
        # We map this to 'customerSummary' field for frontend compatibility
        
        summary_data = agent4_result.data
        
        # Create a markdown representation if not present (frontend might expect 'markdown')
        # Or just save the structured data
        
        try:
            case_ref = self.db.collection('cases').document(case_id)
            analysis_update = {
                'customerSummary': summary_data, # Save structured data directly
                'agents': {
                    'agent4': {
                        'status': 'success',
                        'duration': agent4_result.duration,
                        'retryCount': agent4_result.retry_count,
                        'data': agent4_result.data,
                        'updatedAt': firestore.SERVER_TIMESTAMP,
                    }
                },
                'updatedAt': firestore.SERVER_TIMESTAMP,
            }
            case_ref.set({'analysis': analysis_update}, merge=True)
            logger.info("Agent 4 (Summary) results persisted for case %s", case_id)
        except Exception as exc:
            logger.error("Failed to persist Agent 4 results: %s", exc, exc_info=True)

    async def _run_agent_wrapper(
        self,
        case_id: str,
        agent_id: str,
        runner_func: Callable[..., Awaitable[AgentResult]],
        *args,
        **kwargs
    ) -> AgentResult:
        """Wraps agent execution with retry logic and memory."""
        
        # Check memory
        if self.resume_mode and self.memory:
            cached = self.memory.load_agent_result(case_id, agent_id)
            if cached and cached.success:
                logger.info(f"Resuming {agent_id} from memory")
                return cached

        # Retry loop
        max_attempts = self.agent_retry_attempts + 1 if self.enable_agent_retry else 1
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                result = await runner_func(*args, **kwargs)
                result.retry_count = attempt
                
                if result.success and self.resume_mode and self.memory:
                    self.memory.save_agent_result(case_id, result)
                
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"{agent_id} failed attempt {attempt+1}: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 * (attempt + 1))
        
        return AgentResult(
            agent_id=agent_id,
            success=False,
            error=str(last_error),
            retry_count=max_attempts
        )

    # --- Agent Runners ---

    async def _run_agent_1(self, agent, transcript_segments) -> AgentResult:
        start = time.time()
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: agent.analyze(transcript_segments=transcript_segments))
            # response is now a GeminiResponse object
            return AgentResult(
                "agent1", 
                True, 
                data=response.data, 
                duration=time.time()-start,
                metadata={'report': response.report}  # Store report in metadata
            )
        except Exception as e:
            duration = time.time() - start
            import traceback
            traceback.print_exc()
            logger.error(f"agent1 failed: {str(e)}", exc_info=True)
            return AgentResult(agent_id="agent1", success=False, error=str(e), duration=duration)

    async def _run_agent_2(self, agent, transcript_segments, context_insights) -> AgentResult:
        start = time.time()
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: agent.analyze(transcript_segments=transcript_segments, context_insights=context_insights)
            )
            return AgentResult(
                "agent2", 
                True, 
                data=response.data, 
                duration=time.time()-start,
                metadata={'report': response.report}
            )
        except Exception as e:
            return AgentResult("agent2", False, error=str(e), duration=time.time()-start)

    async def _run_agent_3(self, agent, transcript_segments, context_insights, buyer_insights) -> AgentResult:
        start = time.time()
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: agent.analyze(
                    transcript_segments=transcript_segments, 
                    context_insights=context_insights,
                    buyer_insights=buyer_insights
                )
            )
            return AgentResult(
                "agent3", 
                True, 
                data=response.data, 
                duration=time.time()-start,
                metadata={'report': response.report}
            )
        except Exception as e:
            return AgentResult("agent3", False, error=str(e), duration=time.time()-start)

    async def _run_agent_4(self, agent, transcript_segments, context_insights) -> AgentResult:
        start = time.time()
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: agent.analyze(transcript_segments=transcript_segments, context_insights=context_insights)
            )
            return AgentResult(
                "agent4", 
                True, 
                data=response.data, 
                duration=time.time()-start,
                metadata={'report': response.report}
            )
        except Exception as e:
            return AgentResult("agent4", False, error=str(e), duration=time.time()-start)

    async def analyze_transcript(
        self,
        case_id: str,
        transcript_segments: List[Dict[str, Any]],
        speaker_statistics: Optional[Dict[str, Any]] = None, # Deprecated but kept for sig
        conversation_metadata: Optional[Dict[str, Any]] = None, # Deprecated but kept for sig
    ) -> AnalysisResult:
        """
        Execute the 3+1 Agent Pipeline.
        """
        logger.info(f"Starting V2 (3+1) analysis for case {case_id}")
        start_time = time.time()
        agents = self._ensure_agents()
        agent_results = {}

        # --- Phase 1: Context (Agent 1) ---
        logger.info("Phase 1: Agent 1 (Context)")
        result_a1 = await self._run_agent_wrapper(
            case_id, "agent1", self._run_agent_1, agents['agent1'], transcript_segments
        )
        agent_results['agent1'] = result_a1

        if not result_a1.success:
            logger.error("Agent 1 failed. Aborting pipeline.")
            return AnalysisResult(case_id, False, agent_results, time.time()-start_time, "Agent 1 failed")

        context_insights = result_a1.data

        # --- Phase 2: Buyer (Agent 2) + Summary (Agent 4) ---
        logger.info("Phase 2: Agent 2 (Buyer) & Agent 4 (Summary)")
        result_a2, result_a4 = await asyncio.gather(
            self._run_agent_wrapper(
                case_id, "agent2", self._run_agent_2, agents['agent2'], transcript_segments, context_insights
            ),
            self._run_agent_wrapper(
                case_id, "agent4", self._run_agent_4, agents['agent4'], transcript_segments, context_insights
            )
        )
        agent_results['agent2'] = result_a2
        agent_results['agent4'] = result_a4

        # Persist Agent 4 immediately
        if result_a4.success:
            self._persist_agent4_results(case_id, result_a4)

        if not result_a2.success:
            logger.warning("Agent 2 failed. Agent 3 will have limited context.")
            # We can still try Agent 3 but it might be degraded. For now, let's proceed.
        
        buyer_insights = result_a2.data if result_a2.success else {}

        # --- Phase 3: Seller (Agent 3) ---
        logger.info("Phase 3: Agent 3 (Seller)")
        result_a3 = await self._run_agent_wrapper(
            case_id, "agent3", self._run_agent_3, agents['agent3'], 
            transcript_segments, context_insights, buyer_insights
        )
        agent_results['agent3'] = result_a3

        if result_a3.success:
            self._persist_agent3_results(case_id, result_a3)

        # --- Final Status ---
        success = result_a1.success and result_a2.success and result_a3.success
        total_duration = time.time() - start_time
        
        logger.info(f"Analysis V2 complete. Success: {success}. Duration: {total_duration:.2f}s")

        # --- Send Agent Reports to Slack Thread ---
        # Import here to avoid circular dependency
        try:
            from .slack_notifier import SlackNotifier
            import os
            
            slack_token = os.environ.get('SLACK_BOT_TOKEN')
            if slack_token and self.db:
                logger.info(f"Sending Agent reports to Slack for case {case_id}")
                slack_notifier = SlackNotifier(slack_token, self.db)
                slack_notifier.send_agent_reports(case_id, agent_results)
            else:
                logger.warning("Slack token or DB not available, skipping agent reports")
        except Exception as e:
            logger.error(f"Failed to send agent reports to Slack: {e}", exc_info=True)
            # Don't fail the entire analysis if Slack notification fails

        return AnalysisResult(
            case_id=case_id,
            success=success,
            agent_results=agent_results,
            total_duration=total_duration
        )


