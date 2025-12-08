import json
import os
import logging
from typing import Any, Dict, Optional
from dataclasses import asdict
from .models import AgentResult

logger = logging.getLogger(__name__)

class FileSystemMemory:
    """
    Manages persistent storage of agent results on the filesystem.
    Path structure: memory/runs/{case_id}/{agent_id}.json
    """

    def __init__(self, base_path: str = "memory/runs"):
        self.base_path = base_path

    def _get_file_path(self, case_id: str, agent_id: str) -> str:
        """Constructs the file path for a specific agent result."""
        return os.path.join(self.base_path, case_id, f"{agent_id}.json")

    def _ensure_directory(self, case_id: str):
        """Ensures the directory for the case exists."""
        case_dir = os.path.join(self.base_path, case_id)
        os.makedirs(case_dir, exist_ok=True)

    def save_agent_result(self, case_id: str, result: AgentResult):
        """Saves an AgentResult to the filesystem."""
        if not result.success:
            logger.warning(f"Not saving failed result for {result.agent_id} in case {case_id}")
            return

        try:
            self._ensure_directory(case_id)
            file_path = self._get_file_path(case_id, result.agent_id)
            
            # Convert AgentResult to dict
            data = asdict(result)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved result for {result.agent_id} to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save result for {result.agent_id}: {e}")

    def load_agent_result(self, case_id: str, agent_id: str) -> Optional[AgentResult]:
        """Loads an AgentResult from the filesystem if it exists."""
        file_path = self._get_file_path(case_id, agent_id)
        
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstruct AgentResult
            # Note: We need to handle potential missing fields if AgentResult definition changes
            return AgentResult(**data)
        except Exception as e:
            logger.warning(f"Failed to load result for {agent_id} from {file_path}: {e}")
            return None

    def exists(self, case_id: str, agent_id: str) -> bool:
        """Checks if a result exists for the given agent."""
        return os.path.exists(self._get_file_path(case_id, agent_id))
