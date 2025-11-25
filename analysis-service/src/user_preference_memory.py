import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class UserPreferenceMemory:
    """
    Manages persistent storage of user preferences.
    Path structure: memory/preferences/{user_id}.md
    """

    def __init__(self, base_path: str = "memory/preferences"):
        self.base_path = base_path

    def _get_file_path(self, user_id: str) -> str:
        """Constructs the file path for a specific user's preferences."""
        # Sanitize user_id to prevent path traversal
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ('-', '_'))
        return os.path.join(self.base_path, f"{safe_user_id}.md")

    def _ensure_directory(self):
        """Ensures the preferences directory exists."""
        os.makedirs(self.base_path, exist_ok=True)

    def get_preferences(self, user_id: str) -> Optional[str]:
        """Loads preferences for a specific user."""
        if not user_id:
            return None

        file_path = self._get_file_path(user_id)
        
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            logger.warning(f"Failed to load preferences for {user_id}: {e}")
            return None

    def update_preferences(self, user_id: str, text: str):
        """Updates preferences for a specific user."""
        if not user_id:
            return

        try:
            self._ensure_directory()
            file_path = self._get_file_path(user_id)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            logger.info(f"Updated preferences for {user_id} at {file_path}")
        except Exception as e:
            logger.error(f"Failed to update preferences for {user_id}: {e}")
