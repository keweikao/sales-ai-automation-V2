"""
Token usage tracker for LLM operations.

Tracks token consumption for billing and monitoring.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


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
        "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
        "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    }

    COLLECTION = "llm_usage"

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
        try:
            # Create document data
            data = {
                "conversationId": usage.conversation_id,
                "taskType": usage.task_type,
                "model": usage.model,
                "promptTokens": usage.prompt_tokens,
                "completionTokens": usage.completion_tokens,
                "totalTokens": usage.total_tokens,
                "costUsd": usage.cost_usd,
                "timestamp": usage.timestamp,
                # Add date fields for easier querying
                "date": usage.timestamp.strftime("%Y-%m-%d"),
                "month": usage.timestamp.strftime("%Y-%m"),
            }

            # Add to collection with auto-generated ID
            self.db.collection(self.COLLECTION).add(data)
            logger.debug(f"Persisted token usage: {usage.total_tokens} tokens")

        except Exception as e:
            logger.error(f"Failed to persist token usage: {e}")

    async def get_conversation_usage(self, conversation_id: str) -> dict:
        """Get total usage for a conversation."""
        # First check session cache
        session_total = sum(
            u.total_tokens
            for u in self._session_usage
            if u.conversation_id == conversation_id
        )
        session_cost = sum(
            u.cost_usd
            for u in self._session_usage
            if u.conversation_id == conversation_id
        )

        # Query from Firestore if available
        firestore_total = 0
        firestore_cost = 0.0

        if self.db:
            try:
                query = self.db.collection(self.COLLECTION).where(
                    "conversationId", "==", conversation_id
                )
                for doc in query.stream():
                    data = doc.to_dict()
                    firestore_total += data.get("totalTokens", 0)
                    firestore_cost += data.get("costUsd", 0)
            except Exception as e:
                logger.error(f"Failed to query conversation usage: {e}")

        return {
            "conversation_id": conversation_id,
            "total_tokens": session_total + firestore_total,
            "total_cost_usd": round(session_cost + firestore_cost, 6),
        }

    async def get_daily_usage(self, date: Optional[datetime] = None) -> dict:
        """Get aggregated usage for a day."""
        if date is None:
            date = datetime.utcnow()

        date_str = date.strftime("%Y-%m-%d")

        result = {
            "date": date_str,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "request_count": 0,
            "by_task": {},
            "by_model": {},
        }

        if not self.db:
            return result

        try:
            query = self.db.collection(self.COLLECTION).where("date", "==", date_str)

            for doc in query.stream():
                data = doc.to_dict()
                tokens = data.get("totalTokens", 0)
                cost = data.get("costUsd", 0)
                task = data.get("taskType", "unknown")
                model = data.get("model", "unknown")

                result["total_tokens"] += tokens
                result["total_cost_usd"] += cost
                result["request_count"] += 1

                # Aggregate by task
                if task not in result["by_task"]:
                    result["by_task"][task] = {"tokens": 0, "cost": 0, "count": 0}
                result["by_task"][task]["tokens"] += tokens
                result["by_task"][task]["cost"] += cost
                result["by_task"][task]["count"] += 1

                # Aggregate by model
                if model not in result["by_model"]:
                    result["by_model"][model] = {"tokens": 0, "cost": 0, "count": 0}
                result["by_model"][model]["tokens"] += tokens
                result["by_model"][model]["cost"] += cost
                result["by_model"][model]["count"] += 1

            result["total_cost_usd"] = round(result["total_cost_usd"], 6)

        except Exception as e:
            logger.error(f"Failed to get daily usage: {e}")

        return result

    async def get_monthly_usage(self, month: Optional[str] = None) -> dict:
        """Get aggregated usage for a month."""
        if month is None:
            month = datetime.utcnow().strftime("%Y-%m")

        result = {
            "month": month,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "request_count": 0,
            "daily_breakdown": {},
        }

        if not self.db:
            return result

        try:
            query = self.db.collection(self.COLLECTION).where("month", "==", month)

            for doc in query.stream():
                data = doc.to_dict()
                tokens = data.get("totalTokens", 0)
                cost = data.get("costUsd", 0)
                date = data.get("date", "unknown")

                result["total_tokens"] += tokens
                result["total_cost_usd"] += cost
                result["request_count"] += 1

                # Daily breakdown
                if date not in result["daily_breakdown"]:
                    result["daily_breakdown"][date] = {"tokens": 0, "cost": 0}
                result["daily_breakdown"][date]["tokens"] += tokens
                result["daily_breakdown"][date]["cost"] += cost

            result["total_cost_usd"] = round(result["total_cost_usd"], 6)

        except Exception as e:
            logger.error(f"Failed to get monthly usage: {e}")

        return result

    def get_session_summary(self) -> dict:
        """Get summary of current session usage."""
        if not self._session_usage:
            return {"total_tokens": 0, "total_cost_usd": 0, "requests": 0}

        return {
            "total_tokens": sum(u.total_tokens for u in self._session_usage),
            "total_cost_usd": round(
                sum(u.cost_usd for u in self._session_usage), 6
            ),
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
