"""
Token usage tracker for LLM operations.

Tracks token consumption for billing and monitoring.

NOTE: Existing implementation in src/slack_app/monitoring/token_tracker.py
Will be migrated and extended here.
"""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class TokenUsage:
    """Record of token usage for a single request."""
    conversation_id: Optional[str]
    task_type: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: datetime


class TokenTracker:
    """
    Tracks LLM token usage across the system.

    Provides:
    - Per-conversation tracking
    - Daily/weekly aggregations
    - Cost calculations
    - Usage alerts
    """

    # Cost per 1M tokens (USD)
    COSTS = {
        "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    }

    def __init__(self, db=None):
        self.db = db
        self._session_usage: list[TokenUsage] = []

    async def track(
        self,
        conversation_id: Optional[str],
        task_type: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> TokenUsage:
        """
        Track token usage for a request.

        Args:
            conversation_id: Related conversation
            task_type: Type of LLM task
            model: Model used
            prompt_tokens: Input tokens
            completion_tokens: Output tokens

        Returns:
            TokenUsage record
        """
        cost = self._calculate_cost(model, prompt_tokens, completion_tokens)

        usage = TokenUsage(
            conversation_id=conversation_id,
            task_type=task_type,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=cost,
            timestamp=datetime.utcnow(),
        )

        self._session_usage.append(usage)

        # Persist to Firestore
        if self.db:
            await self._persist(usage)

        return usage

    def _calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate cost in USD."""
        costs = self.COSTS.get(model, {"input": 0, "output": 0})

        input_cost = (prompt_tokens / 1_000_000) * costs["input"]
        output_cost = (completion_tokens / 1_000_000) * costs["output"]

        return round(input_cost + output_cost, 6)

    async def _persist(self, usage: TokenUsage):
        """Persist usage to Firestore."""
        # TODO: Implement Firestore persistence
        pass

    async def get_conversation_usage(self, conversation_id: str) -> dict:
        """Get total usage for a conversation."""
        # TODO: Query from Firestore
        session_total = sum(
            u.total_tokens for u in self._session_usage
            if u.conversation_id == conversation_id
        )
        session_cost = sum(
            u.cost_usd for u in self._session_usage
            if u.conversation_id == conversation_id
        )

        return {
            "conversation_id": conversation_id,
            "total_tokens": session_total,
            "total_cost_usd": session_cost,
        }

    async def get_daily_usage(self, date: Optional[datetime] = None) -> dict:
        """Get aggregated usage for a day."""
        # TODO: Query from Firestore/BigQuery
        return {"message": "Daily usage aggregation not yet implemented"}

    def get_session_summary(self) -> dict:
        """Get summary of current session usage."""
        if not self._session_usage:
            return {"total_tokens": 0, "total_cost_usd": 0, "requests": 0}

        return {
            "total_tokens": sum(u.total_tokens for u in self._session_usage),
            "total_cost_usd": sum(u.cost_usd for u in self._session_usage),
            "requests": len(self._session_usage),
            "by_task": self._aggregate_by_task(),
        }

    def _aggregate_by_task(self) -> dict:
        """Aggregate usage by task type."""
        by_task = {}
        for u in self._session_usage:
            if u.task_type not in by_task:
                by_task[u.task_type] = {"tokens": 0, "cost": 0, "count": 0}
            by_task[u.task_type]["tokens"] += u.total_tokens
            by_task[u.task_type]["cost"] += u.cost_usd
            by_task[u.task_type]["count"] += 1
        return by_task
