import os
import shutil
import pytest
from src.user_preference_memory import UserPreferenceMemory

class TestUserPreferenceMemory:
    @pytest.fixture
    def memory(self):
        base_path = "memory/test_preferences"
        if os.path.exists(base_path):
            shutil.rmtree(base_path)
        yield UserPreferenceMemory(base_path=base_path)
        if os.path.exists(base_path):
            shutil.rmtree(base_path)

    def test_update_and_get_preferences(self, memory):
        user_id = "test_user_1"
        text = "Always be polite."

        # Update
        memory.update_preferences(user_id, text)

        # Verify file exists
        file_path = memory._get_file_path(user_id)
        assert os.path.exists(file_path)

        # Get
        loaded_text = memory.get_preferences(user_id)
        assert loaded_text == text

    def test_get_non_existent_preferences(self, memory):
        result = memory.get_preferences("non_existent_user")
        assert result is None

    def test_path_sanitization(self, memory):
        user_id = "../malicious_user"
        file_path = memory._get_file_path(user_id)
        assert ".." not in file_path
        assert "malicious_user" in file_path
