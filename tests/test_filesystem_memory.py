import os
import json
import shutil
import pytest
from src.filesystem_memory import FileSystemMemory
from src.models import AgentResult

class TestFileSystemMemory:
    @pytest.fixture
    def memory(self):
        base_path = "memory/test_runs"
        if os.path.exists(base_path):
            shutil.rmtree(base_path)
        yield FileSystemMemory(base_path=base_path)
        if os.path.exists(base_path):
            shutil.rmtree(base_path)

    def test_save_and_load_agent_result(self, memory):
        case_id = "test_case_1"
        agent_id = "agent1"
        data = {"key": "value"}
        
        result = AgentResult(
            agent_id=agent_id,
            success=True,
            data=data,
            duration=1.5
        )

        # Save
        memory.save_agent_result(case_id, result)

        # Verify file exists
        file_path = memory._get_file_path(case_id, agent_id)
        assert os.path.exists(file_path)

        # Load
        loaded_result = memory.load_agent_result(case_id, agent_id)
        assert loaded_result is not None
        assert loaded_result.agent_id == agent_id
        assert loaded_result.success is True
        assert loaded_result.data == data
        assert loaded_result.duration == 1.5

    def test_save_failed_result_does_not_save(self, memory):
        case_id = "test_case_2"
        agent_id = "agent1"
        
        result = AgentResult(
            agent_id=agent_id,
            success=False,
            error="Something went wrong"
        )

        memory.save_agent_result(case_id, result)
        
        assert not memory.exists(case_id, agent_id)

    def test_load_non_existent_result(self, memory):
        result = memory.load_agent_result("non_existent", "agent1")
        assert result is None
