"""
Unified LLM client for accessing language models.

Provides a simple interface that routes to the appropriate provider
based on configuration.
"""

from functools import lru_cache
from typing import Any, Optional
import google.generativeai as genai

from core.config import get_settings


class LLMClient:
    """
    Unified client for LLM operations.

    Currently supports:
    - Google Gemini (default)

    Future support planned for:
    - OpenAI
    - Anthropic Claude
    - Local models
    """

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key

        if self.api_key:
            genai.configure(api_key=self.api_key)

        self.default_model = "gemini-2.0-flash"

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
        response_schema: Optional[Any] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The input prompt
            model: Model to use (defaults to gemini-2.0-flash)
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens in response
            response_schema: Pydantic model for structured output
            system_instruction: System-level instructions

        Returns:
            Generated text response
        """
        model_name = model or self.default_model

        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        if response_schema:
            generation_config["response_mime_type"] = "application/json"
            generation_config["response_schema"] = response_schema

        model_instance = genai.GenerativeModel(
            model_name,
            generation_config=generation_config,
            system_instruction=system_instruction,
        )

        response = model_instance.generate_content(prompt)
        return response.text

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
        model: Optional[str] = None,
        temperature: float = 0.3,
        system_instruction: Optional[str] = None,
    ) -> dict:
        """
        Generate structured output matching a schema.

        Args:
            prompt: The input prompt
            response_schema: Pydantic model or dict schema
            model: Model to use
            temperature: Sampling temperature
            system_instruction: System-level instructions

        Returns:
            Parsed response matching the schema
        """
        import json

        response_text = await self.generate(
            prompt=prompt,
            model=model,
            temperature=temperature,
            response_schema=response_schema,
            system_instruction=system_instruction,
        )

        return json.loads(response_text)

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens in text."""
        model_name = model or self.default_model
        model_instance = genai.GenerativeModel(model_name)
        result = model_instance.count_tokens(text)
        return result.total_tokens


@lru_cache()
def get_llm_client() -> LLMClient:
    """Get cached LLM client instance."""
    return LLMClient()
