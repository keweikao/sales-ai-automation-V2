"""
LLM Gateway Service implementation.

Routes requests to appropriate models and tracks usage.
"""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from core.llm import LLMClient

from .tracking.token_tracker import TokenTracker

logger = logging.getLogger(__name__)


class LLMGateway:
    """
    Gateway for all LLM operations.

    Provides:
    - Task-based model routing
    - Token tracking
    - Cost monitoring
    """

    def __init__(self, db=None):
        self.client = LLMClient()
        self._routing_rules = self._load_routing_rules()
        self._model_costs = self._routing_rules.get("costs", {})
        self._token_tracker = TokenTracker(db=db)

    def _load_routing_rules(self) -> dict:
        """Load routing rules from YAML config."""
        config_path = Path(__file__).parent / "routing" / "routing_rules.yaml"

        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded routing rules from {config_path}")

                    # Flatten tasks and default into routing rules
                    rules = {}
                    if "tasks" in config:
                        for task_name, task_config in config["tasks"].items():
                            rules[task_name] = {
                                "model": task_config.get("model", "gemini-2.0-flash"),
                                "temperature": task_config.get("temperature", 0.3),
                                "max_tokens": task_config.get("max_tokens", 4096),
                            }

                    if "default" in config:
                        rules["default"] = {
                            "model": config["default"].get("model", "gemini-2.0-flash"),
                            "temperature": config["default"].get("temperature", 0.3),
                            "max_tokens": config["default"].get("max_tokens", 4096),
                        }
                    elif "default" not in rules:
                        rules["default"] = {
                            "model": "gemini-2.0-flash",
                            "temperature": 0.3,
                            "max_tokens": 4096,
                        }

                    # Store costs separately
                    rules["costs"] = config.get("costs", {})

                    return rules
            else:
                logger.warning(f"Routing config not found at {config_path}, using defaults")
        except Exception as e:
            logger.error(f"Failed to load routing rules: {e}")

        # Fallback to defaults
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

    def get_routing_rules(self) -> dict:
        """Get current routing rules (for debugging/inspection)."""
        return {k: v for k, v in self._routing_rules.items() if k != "costs"}

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
        await self._token_tracker.track(
            conversation_id=conversation_id,
            task_type=task_type,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=response_tokens,
        )

    def get_session_usage(self) -> dict:
        """Get usage summary for current session."""
        return self._token_tracker.get_session_summary()
