"""
Multi-Agent Orchestrator for Sales AI Automation System.

Orchestrates parallel execution of Agent 1-5 for analyzing sales call transcripts,
then sequentially executes Agent 6-7 for synthesis and customer summary generation.

Architecture:
  - Agents 1-5, 7: Execute in parallel using asyncio
  - Agent 6: Synthesizes results from Agents 1-5

Usage:
    orchestrator = MultiAgentOrchestrator()
    results = await orchestrator.analyze_transcript(
        case_id="CASE123",
        transcript_segments=[...],
        speaker_statistics={...}
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

from .agents.agent1_participant import ParticipantProfileAgent
from .agents.agent2_sentiment import SentimentAttitudeAgent
from .agents.agent3_needs import ProductNeedsAgent
from .agents.agent4_competitor import CompetitorAnalysisAgent
from .agents.agent5_questionnaire import QuestionnaireAgent
from .agents.agent6_sales_coach import SalesCoachAgent
from .agents.agent7_customer_summary import CustomerSummaryAgent

logger = logging.getLogger(__name__)


from .models import (
    AgentResult,
    AnalysisResult,
    RetryableError,
    NonRetryableError,
    InsufficientDataError
)
from .filesystem_memory import FileSystemMemory
from .user_preference_memory import UserPreferenceMemory


class MultiAgentOrchestrator:
    """
    Orchestrates parallel execution of multiple AI agents for sales call analysis.
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.2,
        min_success_threshold: int = 3,
        enable_agent_retry: bool = True,
        agent_retry_attempts: int = 2,
        model_config: Optional[Dict[str, str]] = None,
        db_client: Optional[firestore.Client] = None,
        resume_mode: bool = False,
    ):
        """
        Initialize the orchestrator with agent instances.

        Args:
            model_name: Default Gemini model to use for all agents
            temperature: Temperature setting for generation
            min_success_threshold: Minimum number of agents that must succeed (default: 3/5)
            enable_agent_retry: Whether to retry individual agent failures
            agent_retry_attempts: Number of retry attempts per agent (default: 2)
            model_config: Optional dict mapping agent names to specific model names
            resume_mode: If True, try to load previous results from filesystem
        """
        self.model_name = model_name
        self.temperature = temperature
        self.min_success_threshold = min_success_threshold
        self.enable_agent_retry = enable_agent_retry
        self.agent_retry_attempts = agent_retry_attempts
        self.model_config = model_config or {}
        self.db = db_client
        self.resume_mode = resume_mode
        self.memory = FileSystemMemory() if resume_mode else None
        self.preference_memory = UserPreferenceMemory()

        # Initialize agents (will be created on first use to ensure env vars are set)
        self._agents: Optional[Dict[str, Any]] = None

    def _persist_agent6_results(self, case_id: str, agent6_result: AgentResult) -> None:
        """Persist Agent 6 (structured + raw output) to Firestore."""
        if not self.db or not agent6_result.success or not agent6_result.data:
            return

        structured = agent6_result.data.get('structured')
        raw_output = agent6_result.data.get('rawOutput')

        if not structured and not raw_output:
            return

        try:
            case_ref = self.db.collection('cases').document(case_id)
            analysis_update: Dict[str, Any] = {}

            if structured is not None:
                analysis_update['structured'] = structured
            if raw_output is not None:
                analysis_update['rawOutput'] = raw_output

            agents_section = analysis_update.setdefault('agents', {})
            agents_section['agent6'] = {
                'status': 'success',
                'duration': agent6_result.duration,
                'retryCount': agent6_result.retry_count,
                'data': agent6_result.data,
                'updatedAt': firestore.SERVER_TIMESTAMP,
            }
            analysis_update['updatedAt'] = firestore.SERVER_TIMESTAMP

            case_ref.set({'analysis': analysis_update}, merge=True)
            logger.info("Agent 6 results persisted for case %s", case_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Failed to persist Agent 6 results for case %s: %s",
                case_id,
                exc,
                exc_info=True,
            )

    def _persist_agent7_results(self, case_id: str, agent7_result: AgentResult) -> None:
        """Persist Agent 7 summary + markdown to Firestore."""
        if not self.db or not agent7_result.success or not agent7_result.data:
            return

        summary_payload = agent7_result.data.get('customerSummary') or {}
        markdown = agent7_result.data.get('markdown')

        if not summary_payload and not markdown:
            return

        summary_doc = copy.deepcopy(summary_payload)

        if markdown:
            summary_doc['markdown'] = markdown
            summary_doc.setdefault('originalMarkdown', markdown)

        summary_doc.setdefault('isEdited', False)
        summary_doc.setdefault('editCount', 0)
        summary_doc.setdefault('editedBy', None)
        summary_doc.setdefault('editHistory', [])
        summary_doc.setdefault('lastEditedAt', firestore.SERVER_TIMESTAMP)

        try:
            case_ref = self.db.collection('cases').document(case_id)
            analysis_update = {
                'customerSummary': summary_doc,
                'agents': {
                    'agent7': {
                        'status': 'success',
                        'duration': agent7_result.duration,
                        'retryCount': agent7_result.retry_count,
                        'data': agent7_result.data,
                        'updatedAt': firestore.SERVER_TIMESTAMP,
                    }
                },
                'updatedAt': firestore.SERVER_TIMESTAMP,
            }
            case_ref.set({'analysis': analysis_update}, merge=True)
            logger.info("Agent 7 summary persisted for case %s", case_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Failed to persist Agent 7 summary for case %s: %s",
                case_id,
                exc,
                exc_info=True,
            )

    def _ensure_agents(self) -> Dict[str, Any]:
        """Lazy initialization of agent instances."""
        if self._agents is None:
            logger.info("Initializing Agent 1-7 instances...")
            self._agents = {
                "agent1": ParticipantProfileAgent(
                    model_name=self.model_config.get("agent1", self.model_name),
                    temperature=self.temperature
                ),
                "agent2": SentimentAttitudeAgent(
                    model_name=self.model_config.get("agent2", self.model_name),
                    temperature=self.temperature
                ),
                "agent3": ProductNeedsAgent(
                    model_name=self.model_config.get("agent3", self.model_name),
                    temperature=self.temperature
                ),
                "agent4": CompetitorAnalysisAgent(
                    model_name=self.model_config.get("agent4", self.model_name),
                    temperature=self.temperature
                ),
                "agent5": QuestionnaireAgent(
                    model_name=self.model_config.get("agent5", self.model_name),
                    temperature=self.temperature
                ),
                "agent6": SalesCoachAgent(
                    model_name=self.model_config.get("agent6", self.model_name),
                    temperature=self.temperature
                ),
                "agent7": CustomerSummaryAgent(
                    model_name=self.model_config.get("agent7", self.model_name),
                    temperature=self.temperature
                ),
            }
            logger.info(f"Initialized {len(self._agents)} agents successfully")
        return self._agents

    def _classify_error(self, error: Exception) -> str:
        """
        Classify error as retryable or non-retryable.

        Retryable errors:
        - Network timeouts
        - Rate limits (429)
        - Temporary service unavailable (503)
        - JSON parsing errors (LLM output issues)

        Non-retryable errors:
        - Authentication errors (401, 403)
        - Invalid input format
        - Configuration errors
        """
        error_str = str(error).lower()

        # Retryable patterns
        retryable_patterns = [
            'timeout', 'timed out',
            'rate limit', '429',
            'service unavailable', '503',
            'connection', 'network',
            'json', 'parse',
            'temporary', 'transient',
        ]

        for pattern in retryable_patterns:
            if pattern in error_str:
                return 'retryable'

        # Non-retryable patterns
        non_retryable_patterns = [
            'unauthorized', '401',
            'forbidden', '403',
            'not found', '404',
            'invalid', 'bad request', '400',
            'api key', 'authentication',
        ]

        for pattern in non_retryable_patterns:
            if pattern in error_str:
                return 'non_retryable'

        # Default: treat as retryable to be safe
        return 'retryable'

    async def _run_agent_with_retry(
        self,
        agent_id: str,
        agent: Any,
        transcript_segments: List[Dict[str, Any]],
        speaker_statistics: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
        case_id: Optional[str] = None,
    ) -> AgentResult:
        """
        Execute agent with retry logic for transient failures.
        Supports filesystem memory resume if enabled.

        Returns:
            AgentResult with retry_count populated
        """
        # Check filesystem memory first if resume mode is on
        if self.resume_mode and self.memory and case_id:
            cached_result = self.memory.load_agent_result(case_id, agent_id)
            if cached_result and cached_result.success:
                logger.info(f"Resuming {agent_id} from filesystem memory for case {case_id}")
                return cached_result
        max_attempts = self.agent_retry_attempts + 1 if self.enable_agent_retry else 1
        last_error = None
        error_type = None

        for attempt in range(max_attempts):
            try:
                result = await self._run_agent_async(
                    agent_id=agent_id,
                    agent=agent,
                    transcript_segments=transcript_segments,
                    speaker_statistics=speaker_statistics,
                    conversation_metadata=conversation_metadata,
                )
                result.retry_count = attempt
                
                # Save to memory if successful and enabled
                if result.success and self.resume_mode and self.memory and case_id:
                    self.memory.save_agent_result(case_id, result)
                
                return result

            except Exception as e:
                last_error = e
                error_type = self._classify_error(e)

                if error_type == 'non_retryable':
                    logger.warning(f"{agent_id} failed with non-retryable error: {e}")
                    break

                if attempt < max_attempts - 1:
                    backoff_time = 5 * (2 ** attempt)  # 5s, 10s
                    logger.warning(
                        f"{agent_id} failed (attempt {attempt + 1}/{max_attempts}), "
                        f"retrying in {backoff_time}s: {e}"
                    )
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(
                        f"{agent_id} failed after {max_attempts} attempts: {e}"
                    )

        # All attempts failed
        return AgentResult(
            agent_id=agent_id,
            success=False,
            error=str(last_error),
            error_type=error_type,
            retry_count=max_attempts - 1,
        )

    async def _run_agent_wrapper(
        self,
        case_id: str,
        agent_id: str,
        runner_func: Callable[..., Awaitable[AgentResult]],
        *args,
        **kwargs
    ) -> AgentResult:
        """
        Wraps agent execution with filesystem memory check and persistence.
        """
        # Check filesystem memory first if resume mode is on
        if self.resume_mode and self.memory:
            cached_result = self.memory.load_agent_result(case_id, agent_id)
            if cached_result and cached_result.success:
                logger.info(f"Resuming {agent_id} from filesystem memory for case {case_id}")
                return cached_result

        # Run the actual agent runner
        result = await runner_func(*args, **kwargs)

        # Save to memory if successful and enabled
        if result.success and self.resume_mode and self.memory:
            self.memory.save_agent_result(case_id, result)

        return result

    async def _run_agent_1(
        self,
        agent,
        transcript_segments,
        speaker_statistics,
        conversation_metadata
    ) -> AgentResult:
        """Run Agent 1 (Participant) with speaker_statistics."""
        start_time = time.time()
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent.analyze(
                    transcript_segments=transcript_segments,
                    speaker_statistics=speaker_statistics,
                    conversation_metadata=conversation_metadata,
                )
            )
            duration = time.time() - start_time
            logger.info(f"agent1 completed successfully in {duration:.2f}s")
            return AgentResult(agent_id="agent1", success=True, data=result, duration=duration)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"agent1 failed: {str(e)}", exc_info=True)
            return AgentResult(agent_id="agent1", success=False, error=str(e), duration=duration)

    async def _run_agent_2(
        self,
        agent,
        transcript_segments,
        participant_insights,
        conversation_metadata
    ) -> AgentResult:
        """Run Agent 2 (Sentiment) with participant_insights."""
        start_time = time.time()
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent.analyze(
                    transcript_segments=transcript_segments,
                    participant_insights=participant_insights,
                    conversation_metadata=conversation_metadata,
                )
            )
            duration = time.time() - start_time
            logger.info(f"agent2 completed successfully in {duration:.2f}s")
            return AgentResult(agent_id="agent2", success=True, data=result, duration=duration)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"agent2 failed: {str(e)}", exc_info=True)
            return AgentResult(agent_id="agent2", success=False, error=str(e), duration=duration)

    async def _run_agent_3(
        self,
        agent,
        transcript_segments,
        participant_insights,
        sentiment_insights,
        conversation_metadata
    ) -> AgentResult:
        """Run Agent 3 (Needs) with participant and sentiment insights."""
        start_time = time.time()
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent.analyze(
                    transcript_segments=transcript_segments,
                    participant_insights=participant_insights,
                    sentiment_insights=sentiment_insights,
                    conversation_metadata=conversation_metadata,
                )
            )
            duration = time.time() - start_time
            logger.info(f"agent3 completed successfully in {duration:.2f}s")
            return AgentResult(agent_id="agent3", success=True, data=result, duration=duration)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"agent3 failed: {str(e)}", exc_info=True)
            return AgentResult(agent_id="agent3", success=False, error=str(e), duration=duration)

    async def _run_agent_4(
        self,
        agent,
        transcript_segments,
        participant_insights,
        sentiment_insights,
        conversation_metadata
    ) -> AgentResult:
        """Run Agent 4 (Competitor) with participant and sentiment insights."""
        start_time = time.time()
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent.analyze(
                    transcript_segments=transcript_segments,
                    participant_insights=participant_insights,
                    sentiment_insights=sentiment_insights,
                    conversation_metadata=conversation_metadata,
                )
            )
            duration = time.time() - start_time
            logger.info(f"agent4 completed successfully in {duration:.2f}s")
            return AgentResult(agent_id="agent4", success=True, data=result, duration=duration)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"agent4 failed: {str(e)}", exc_info=True)
            return AgentResult(agent_id="agent4", success=False, error=str(e), duration=duration)

    async def _run_agent_5(
        self,
        agent,
        transcript_segments,
        participant_insights,
        sentiment_insights,
        product_needs,
        conversation_metadata
    ) -> AgentResult:
        """Run Agent 5 (Questionnaire) with all previous insights."""
        start_time = time.time()
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent.analyze(
                    transcript_segments=transcript_segments,
                    participant_insights=participant_insights,
                    sentiment_insights=sentiment_insights,
                    product_needs=product_needs,
                    conversation_metadata=conversation_metadata,
                )
            )
            duration = time.time() - start_time
            logger.info(f"agent5 completed successfully in {duration:.2f}s")
            return AgentResult(agent_id="agent5", success=True, data=result, duration=duration)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"agent5 failed: {str(e)}", exc_info=True)
            return AgentResult(agent_id="agent5", success=False, error=str(e), duration=duration)

    async def _run_agent_6(
        self,
        agent,
        transcript_segments,
        agent_context,
        case_metadata,
        conversation_metadata,
    ) -> AgentResult:
        """Run Agent 6 (Sales Coach) using aggregated context."""
        start_time = time.time()
        
        # Retrieve user preferences if salesRepId is available
        user_preferences = None
        if case_metadata and "salesRepId" in case_metadata:
             user_preferences = self.preference_memory.get_preferences(case_metadata["salesRepId"])

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent.analyze(
                    agent_outputs=agent_context,
                    transcript_segments=transcript_segments,
                    case_metadata=case_metadata,
                    conversation_metadata=conversation_metadata,
                    user_preferences=user_preferences,
                ),
            )
            duration = time.time() - start_time
            logger.info(f"agent6 completed successfully in {duration:.2f}s")
            return AgentResult(agent_id="agent6", success=True, data=result, duration=duration)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"agent6 failed: {str(e)}", exc_info=True)
            return AgentResult(agent_id="agent6", success=False, error=str(e), duration=duration)

    async def _run_agent_7(
        self,
        agent,
        transcript_segments,
        case_metadata,
        conversation_metadata
    ) -> AgentResult:
        """Run Agent 7 (Customer Summary) independently."""
        start_time = time.time()
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent.analyze(
                    transcript_segments=transcript_segments,
                    case_metadata=case_metadata,
                    conversation_metadata=conversation_metadata,
                )
            )
            duration = time.time() - start_time
            logger.info(f"agent7 completed successfully in {duration:.2f}s")
            return AgentResult(agent_id="agent7", success=True, data=result, duration=duration)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"agent7 failed: {str(e)}", exc_info=True)
            return AgentResult(agent_id="agent7", success=False, error=str(e), duration=duration)

    def _build_agent6_context(self, agent_results: Dict[str, AgentResult]) -> Dict[str, Any]:
        """Map Agent 1-5 outputs to Agent 6 input keys."""
        mapping = {
            "agent1": "agent1_participant",
            "agent2": "agent2_sentiment",
            "agent3": "agent3_needs",
            "agent4": "agent4_competitor",
            "agent5": "agent5_questionnaire",
        }
        context: Dict[str, Any] = {}
        for src, target in mapping.items():
            result = agent_results.get(src)
            if result and result.success and result.data:
                context[target] = result.data
        return context

    def _build_failed_result(self, case_id: str, agent_results: dict, start_time: float) -> AnalysisResult:
        """Build a failed AnalysisResult when Agent 1 fails."""
        total_duration = time.time() - start_time
        return AnalysisResult(
            case_id=case_id,
            success=False,
            agent_results=agent_results,
            total_duration=total_duration,
            error="Agent 1 (Participant) failed - cannot continue pipeline"
        )

    async def analyze_transcript(
        self,
        case_id: str,
        transcript_segments: List[Dict[str, Any]],
        speaker_statistics: Optional[Dict[str, Any]] = None,
        conversation_metadata: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        Execute Agents 1-7, with parallel execution where possible.

        Agent execution order:
        1. Agent 1 (Participant) - uses speaker_statistics
        2. Agent 2 (Sentiment) - uses Agent 1's output as participant_insights
        3. Agents 3, 4, 7 (Needs, Competitor, Customer Summary) - run in parallel
        4. Agent 5 (Questionnaire) - uses Agent 1, 2, 3's outputs
        5. Agent 6 (Sales Coach) - uses transcript + Agent 1-5 outputs

        Args:
            case_id: Unique identifier for the case
            transcript_segments: List of transcript segments with speaker info
            speaker_statistics: Speaker time percentages (e.g., {"Speaker 1": 45.2})
            conversation_metadata: Additional context about the conversation

        Returns:
            AnalysisResult containing all agent outputs and metadata
        """
        logger.info(f"Starting multi-agent sequential analysis for case {case_id}")
        start_time = time.time()

        agents = self._ensure_agents()
        agent_results = {}

        # --- Phase 1: Agents 1, 5, 7 (Participant, Questionnaire, Summary) in parallel ---
        logger.info("Phase 1: Executing Agents 1, 5, 7 in parallel")
        
        # Prepare metadata for Agent 7
        case_metadata = {
            "caseId": case_id,
            "customer": {
                "storeName": (conversation_metadata or {}).get("storeName"),
                "customerId": (conversation_metadata or {}).get("customerId"),
            },
        }

        result_agent1, result_agent5, result_agent7 = await asyncio.gather(
            self._run_agent_wrapper(
                case_id, "agent1", self._run_agent_1,
                agents['agent1'],
                transcript_segments,
                speaker_statistics,
                conversation_metadata
            ),
            self._run_agent_wrapper(
                case_id, "agent5", self._run_agent_5,
                agents['agent5'],
                transcript_segments,
                None, # participant_insights
                None, # sentiment_insights
                None, # product_needs
                conversation_metadata
            ),
            self._run_agent_wrapper(
                case_id, "agent7", self._run_agent_7,
                agents['agent7'],
                transcript_segments,
                case_metadata,
                conversation_metadata
            ),
            return_exceptions=False
        )
        
        agent_results['agent1'] = result_agent1
        agent_results['agent5'] = result_agent5
        agent_results['agent7'] = result_agent7

        if not result_agent1.success:
            logger.error("Agent 1 failed - aborting analysis pipeline")
            return self._build_failed_result(case_id, agent_results, start_time)

        # --- Phase 2: Agent 2 (Sentiment) ---
        logger.info("Phase 2: Executing Agent 2 (Sentiment)")
        result_agent2 = await self._run_agent_wrapper(
            case_id, "agent2", self._run_agent_2,
            agents['agent2'],
            transcript_segments,
            result_agent1.data,
            conversation_metadata
        )
        agent_results['agent2'] = result_agent2

        if not result_agent2.success:
            logger.warning("Agent 2 failed - continuing with limited data")

        # --- Phase 3: Agents 3, 4 (Needs, Competitor) in parallel ---
        logger.info("Phase 3: Executing Agents 3, 4 in parallel")
        result_agent3, result_agent4 = await asyncio.gather(
            self._run_agent_wrapper(
                case_id, "agent3", self._run_agent_3,
                agents['agent3'],
                transcript_segments,
                result_agent1.data,
                result_agent2.data if result_agent2.success else None,
                conversation_metadata
            ),
            self._run_agent_wrapper(
                case_id, "agent4", self._run_agent_4,
                agents['agent4'],
                transcript_segments,
                result_agent1.data,
                result_agent2.data if result_agent2.success else None,
                conversation_metadata
            ),
            return_exceptions=False
        )
        agent_results['agent3'] = result_agent3
        agent_results['agent4'] = result_agent4

        # --- Phase 5: Agent 6 (Sales Coach) ---
        successful_so_far = [r for r in agent_results.values() if r.success and r.agent_id in ["agent1", "agent2", "agent3", "agent4", "agent5"]]
        if len(successful_so_far) >= self.min_success_threshold:
            logger.info("Phase 5: Executing Agent 6 (Sales Coach)")
            agent6_context = self._build_agent6_context(agent_results)
            result_agent6 = await self._run_agent_wrapper(
                case_id, "agent6", self._run_agent_6,
                agents['agent6'],
                transcript_segments,
                agent6_context,
                case_metadata,
                conversation_metadata,
            )
            agent_results['agent6'] = result_agent6
        else:
            logger.warning(
                "Skipping Agent 6 for case %s due to insufficient upstream success (%d/%d)",
                case_id,
                len(successful_so_far),
                self.min_success_threshold,
            )

        # --- Final Summary ---
        total_duration = time.time() - start_time
        successful_results = [r for r in agent_results.values() if r.success]
        failed_results = [r for r in agent_results.values() if not r.success]
        success_count = len(successful_results)

        # Success of the main pipeline (1-6) is determined by the threshold
        main_pipeline_agents = {k: v for k, v in agent_results.items() if k != 'agent7'}
        main_pipeline_success_count = len([r for r in main_pipeline_agents.values() if r.success and r.agent_id in ["agent1", "agent2", "agent3", "agent4", "agent5"]])
        
        success = main_pipeline_success_count >= self.min_success_threshold
        error = None

        if not success:
            failed_main_agents = [r.agent_id for r in main_pipeline_agents.values() if not r.success]
            error = (
                f"Insufficient data: only {main_pipeline_success_count}/{len(main_pipeline_agents)} main agents succeeded "
                f"(minimum required: {self.min_success_threshold}). "
                f"Failed agents: {', '.join(failed_main_agents)}"
            )
            logger.error(f"Analysis failed for case {case_id}: {error}")
        elif failed_results:
            failed_agents = [r.agent_id for r in failed_results]
            logger.warning(
                f"Analysis completed with partial success for case {case_id}: "
                f"{success_count}/{len(agents)} agents succeeded. "
                f"Failed: {', '.join(failed_agents)}"
            )
        else:
            logger.info(
                f"Analysis completed successfully for case {case_id} in {total_duration:.2f}s"
            )

        # --- Firestore Persistence for Agent 6 & 7 ---
        agent6_result = agent_results.get('agent6')
        if agent6_result:
            self._persist_agent6_results(case_id, agent6_result)

        agent7_result = agent_results.get('agent7')
        if agent7_result:
            self._persist_agent7_results(case_id, agent7_result)


        return AnalysisResult(
            case_id=case_id,
            success=success,
            agent_results=agent_results,
            total_duration=total_duration,
            error=error,
        )

    def get_analysis_summary(self, result: AnalysisResult) -> Dict[str, Any]:
        """
        Generate a summary of the analysis results.

        Args:
            result: AnalysisResult from analyze_transcript()

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "case_id": result.case_id,
            "success": result.success,
            "total_duration": round(result.total_duration, 2),
            "agents": {},
        }

        for agent_id, agent_result in result.agent_results.items():
            summary["agents"][agent_id] = {
                "success": agent_result.success,
                "duration": round(agent_result.duration, 2),
                "has_data": agent_result.data is not None,
            }
            if agent_result.error:
                summary["agents"][agent_id]["error"] = agent_result.error

        return summary
