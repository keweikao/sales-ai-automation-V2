import pytest
from unittest.mock import MagicMock, patch
from src.agents.agent6_sales_coach import SalesCoachAgent

class TestAgent6Preferences:
    def test_build_prompt_includes_preferences(self):
        agent = SalesCoachAgent(model_name="test-model")
        
        preferences = "IMPORTANT: Focus on closing techniques."
        
        prompt = agent.build_prompt(
            transcript_text="Customer: Hello.",
            user_preferences=preferences
        )
        
        assert "=== User Preferences (MUST FOLLOW) ===" in prompt
        assert preferences in prompt

    def test_build_prompt_without_preferences(self):
        agent = SalesCoachAgent(model_name="test-model")
        
        prompt = agent.build_prompt(
            transcript_text="Customer: Hello."
        )
        
        assert "=== User Preferences (MUST FOLLOW) ===" not in prompt
