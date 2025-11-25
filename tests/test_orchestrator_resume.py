import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.orchestrator import MultiAgentOrchestrator
from src.models import AgentResult

@pytest.mark.asyncio
class TestOrchestratorResume:
    async def test_orchestrator_resume_capability(self, tmp_path):
        """
        Test that the orchestrator skips already completed agents when resume_mode is True.
        """
        # Setup temporary memory path
        memory_path = tmp_path / "memory"
        
        # Mock agents
        mock_agents = {
            f"agent{i}": MagicMock() for i in range(1, 8)
        }
        
        # Create orchestrator with resume_mode=True
        orchestrator = MultiAgentOrchestrator(resume_mode=True)
        # Override memory base path for testing
        orchestrator.memory.base_path = str(memory_path)
        # Inject mock agents
        orchestrator._agents = mock_agents

        # Case ID
        case_id = "resume_test_case"

        # --- Run 1: Simulate Agent 1 success, Agent 2 failure ---
        
        # Mock Agent 1 success
        orchestrator._run_agent_1 = AsyncMock(return_value=AgentResult(
            agent_id="agent1", success=True, data={"profile": "test"}
        ))
        
        # Mock Agent 5 success (runs in parallel with 1)
        orchestrator._run_agent_5 = AsyncMock(return_value=AgentResult(
            agent_id="agent5", success=True, data={"q": "a"}
        ))

        # Mock Agent 7 success (runs in parallel with 1)
        orchestrator._run_agent_7 = AsyncMock(return_value=AgentResult(
            agent_id="agent7", success=True, data={"summary": "test"}
        ))

        # Mock Agent 2 FAILURE
        orchestrator._run_agent_2 = AsyncMock(return_value=AgentResult(
            agent_id="agent2", success=False, error="Simulated failure"
        ))

        # Mock downstream agents to FAIL in Run 1 (so overall result is failure)
        orchestrator._run_agent_3 = AsyncMock(return_value=AgentResult(agent_id="agent3", success=False))
        orchestrator._run_agent_4 = AsyncMock(return_value=AgentResult(agent_id="agent4", success=False))
        orchestrator._run_agent_6 = AsyncMock(return_value=AgentResult(agent_id="agent6", success=False))

        # Run analysis
        result1 = await orchestrator.analyze_transcript(
            case_id=case_id,
            transcript_segments=[],
            speaker_statistics={}
        )

        # Verify Run 1 failed
        assert not result1.success
        assert result1.agent_results["agent1"].success
        assert result1.agent_results["agent2"].success is False
        
        # Verify Agent 1 result is saved to disk
        assert orchestrator.memory.exists(case_id, "agent1")
        assert not orchestrator.memory.exists(case_id, "agent2") # Failed, so not saved

        # --- Run 2: Fix Agent 2, verify Agent 1 is NOT re-run ---
        
        # Reset mocks to track calls
        orchestrator._run_agent_1.reset_mock()
        orchestrator._run_agent_5.reset_mock()
        orchestrator._run_agent_7.reset_mock()
        
        # Mock Agent 2 SUCCESS now
        orchestrator._run_agent_2 = AsyncMock(return_value=AgentResult(
            agent_id="agent2", success=True, data={"sentiment": "positive"}
        ))
        
        # Mock downstream agents success
        orchestrator._run_agent_3 = AsyncMock(return_value=AgentResult(agent_id="agent3", success=True, data={}))
        orchestrator._run_agent_4 = AsyncMock(return_value=AgentResult(agent_id="agent4", success=True, data={}))
        orchestrator._run_agent_6 = AsyncMock(return_value=AgentResult(agent_id="agent6", success=True, data={}))

        # Run analysis again
        result2 = await orchestrator.analyze_transcript(
            case_id=case_id,
            transcript_segments=[],
            speaker_statistics={}
        )

        # Verify Run 2 success
        assert result2.success
        
        # CRITICAL: Verify Agent 1, 5, 7 were NOT re-run (call count should be 0 because wrapper intercepted it)
        # Wait, the wrapper calls the runner_func. If wrapper intercepts, runner_func is NOT called.
        # So mock call count should be 0.
        orchestrator._run_agent_1.assert_not_called()
        orchestrator._run_agent_5.assert_not_called()
        orchestrator._run_agent_7.assert_not_called()
        
        # Verify Agent 2 WAS called (since it wasn't in memory)
        orchestrator._run_agent_2.assert_called_once()

