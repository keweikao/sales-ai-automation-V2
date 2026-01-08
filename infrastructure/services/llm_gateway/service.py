"""
LLM Gateway Service implementation.

Routes requests to appropriate models and tracks usage.
"""

from typing import Any, Optional
from core.llm import LLMClient


class LLMGateway:
    """
    Gateway for all LLM operations.

    Provides:
    - Task-based model routing
    - Token tracking
    - Cost monitoring
    """

    def __init__(self):
        self.client = LLMClient()
        self._routing_rules = self._load_routing_rules()

    def _load_routing_rules(self) -> dict:
        """Load routing rules from config."""
        # TODO: Load from routing/routing_rules.yaml
        return {
            "meddic_analysis": {
                "model": "gemini-2.0-flash",
                "temperature": 0.3,
                "max_tokens": 8192,
            },
            "summary_generation": {
                "model": "gemini-2.0-flash",
                "temperature": 0.5,
                "max_tokens": 4096,
            },
            "coaching": {
                "model": "gemini-2.0-flash",
                "temperature": 0.4,
                "max_tokens": 4096,
            },
            "default": {
                "model": "gemini-2.0-flash",
                "temperature": 0.3,
                "max_tokens": 4096,
            },
        }

    async def generate(
        self,
        prompt: str,
        task_type: str = "default",
        conversation_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Generate text using the appropriate model for the task.

        Args:
            prompt: Input prompt
            task_type: Type of task for routing
            conversation_id: For tracking purposes
            **kwargs: Override routing parameters

        Returns:
            Generated text
        """
        # Get routing config
        config = self._routing_rules.get(task_type, self._routing_rules["default"])

        # Apply overrides
        model = kwargs.get("model", config["model"])
        temperature = kwargs.get("temperature", config["temperature"])
        max_tokens = kwargs.get("max_tokens", config["max_tokens"])

        # Generate
        response = await self.client.generate(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Track usage
        await self._track_usage(
            conversation_id=conversation_id,
            task_type=task_type,
            model=model,
            prompt_tokens=await self.client.count_tokens(prompt),
            response_tokens=await self.client.count_tokens(response),
        )

        return response

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
        task_type: str = "default",
        conversation_id: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """
        Generate structured output.

        Args:
            prompt: Input prompt
            response_schema: Pydantic model or dict schema
            task_type: Type of task for routing
            conversation_id: For tracking
            **kwargs: Override parameters

        Returns:
            Parsed response matching schema
        """
        config = self._routing_rules.get(task_type, self._routing_rules["default"])

        return await self.client.generate_structured(
            prompt=prompt,
            response_schema=response_schema,
            model=kwargs.get("model", config["model"]),
            temperature=kwargs.get("temperature", config["temperature"]),
        )

    async def _track_usage(
        self,
        conversation_id: Optional[str],
        task_type: str,
        model: str,
        prompt_tokens: int,
        response_tokens: int,
    ):
        """Track token usage for billing and monitoring."""
        # TODO: Delegate to tracking/token_tracker.py
        pass
