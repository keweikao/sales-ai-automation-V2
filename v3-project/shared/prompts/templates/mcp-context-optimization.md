# MCP Context Optimization Prompt Template

**Purpose**: Guide tool implementations to filter data in execution environment before passing to model context.

**Source**: Derived from Anthropic official doc (2025) - <https://www.anthropic.com/engineering/code-execution-with-mcp>

**Token Optimization**: Achieve 98%+ token reduction for large datasets (Anthropic case study: 150k → 2k tokens).

---

## Core Principle

```
# derived from Anthropic official doc (2025)

CRITICAL DESIGN PRINCIPLE:
Data filtering MUST occur in the execution environment, NOT in model context.

❌ WRONG APPROACH:
1. Query returns 10,000 records
2. Pass all 10,000 records to model (500k tokens)
3. Model filters to 50 relevant records
→ Result: 500k tokens used

✅ CORRECT APPROACH:
1. Query returns 10,000 records (in execution environment)
2. Filter to 50 relevant records IN ENVIRONMENT (using Python/pandas)
3. Pass only 50 records to model (2k tokens)
→ Result: 2k tokens used (99.6% savings)

KEY INSIGHT: Intermediate results stay in execution environment, never enter model.
```

---

## Implementation Pattern for Tools

### Standard Tool Template

```python
# tools/firestore/query.py

"""
Tool: firestore_query
Description: Query Firestore with automatic context optimization

# derived from Anthropic official doc (2025)
"""

def firestore_query(
    collection: str,
    filters: list[dict],
    order_by: str = None,
    limit: int = 100,
    context_mode: str = "minimal"  # KEY PARAMETER
) -> dict:
    """
    Query Firestore with automatic context optimization.

    Args:
        collection: Collection name
        filters: List of filter conditions
        order_by: Sort field (optional)
        limit: Max results to return
        context_mode: "minimal" | "full" | "aggregate"
            - minimal: Return only essential fields (4-6 fields per record)
            - full: Return all fields (use only for <10 results)
            - aggregate: Return statistics only (no individual records)

    Returns:
        Filtered, PII-protected results optimized for model context
    """

    # =====================================
    # STAGE 1: QUERY EXECUTION (in environment)
    # =====================================
    query = firestore_client.collection(collection)

    for f in filters:
        query = query.where(f["field"], f["op"], f["value"])

    if order_by:
        query = query.order_by(order_by)

    raw_results = query.limit(limit * 2).get()  # Fetch extra for filtering
    # At this point: raw_results might be 1000+ records with 50+ fields each
    # Estimated tokens: ~500,000 tokens
    # ❌ DO NOT pass raw_results to model!

    # =====================================
    # STAGE 2: FIELD FILTERING (in environment)
    # =====================================
    if context_mode == "minimal":
        # Extract only essential fields
        ESSENTIAL_FIELDS = [
            "case_id",
            "customer_name",
            "rep_name",
            "health_score",
            "created_date",
            "status"
        ]

        filtered_results = [
            {k: doc.get(k) for k in ESSENTIAL_FIELDS if k in doc}
            for doc in raw_results
        ]
        # Reduced from 50 fields → 6 fields per record
        # Token reduction: ~88% at this stage

    elif context_mode == "aggregate":
        # Compute statistics in environment, return summary only
        import pandas as pd

        df = pd.DataFrame([doc.to_dict() for doc in raw_results])

        filtered_results = {
            "total_count": len(df),
            "avg_health_score": float(df["health_score"].mean()),
            "median_health_score": float(df["health_score"].median()),
            "min_health_score": float(df["health_score"].min()),
            "max_health_score": float(df["health_score"].max()),
            "by_rep": df.groupby("rep_name")["health_score"].mean().to_dict(),
            "by_status": df.groupby("status").size().to_dict()
        }
        # Token reduction: ~99% (no individual records passed)

    else:  # context_mode == "full"
        filtered_results = [doc.to_dict() for doc in raw_results]
        # ⚠️ Only use for <10 results!

    # =====================================
    # STAGE 3: PII ANONYMIZATION (in environment)
    # =====================================
    # This happens automatically in mcp_adapter.py via PIIAnonymizer
    # But tools can also do explicit anonymization:
    for record in filtered_results:
        if "customer_email" in record:
            record["customer_email"] = "[REDACTED]"
        if "customer_phone" in record:
            record["customer_phone"] = "[REDACTED]"

    # =====================================
    # STAGE 4: RESULT RANKING & TRUNCATION (in environment)
    # =====================================
    if len(filtered_results) > limit:
        # Apply relevance ranking logic
        filtered_results = _rank_by_relevance(filtered_results, filters)
        filtered_results = filtered_results[:limit]

    # =====================================
    # STAGE 5: RETURN TO MODEL
    # =====================================
    return {
        "results": filtered_results,  # Now optimized for context
        "total_count": len(raw_results),
        "returned_count": len(filtered_results),
        "truncated": len(raw_results) > len(filtered_results),
        "context_mode": context_mode
    }
    # Final token count: ~2,000 tokens (vs. 500,000 raw)
    # Reduction: 99.6%
```

---

## Context Mode Selection Guide

### When to use each mode

| Context Mode | Use Case | Token Impact | Example Query |
|--------------|----------|--------------|---------------|
| **minimal** | Expected 10+ results, need basic info | 96-98% reduction | "王小明這週的案件？" |
| **aggregate** | Statistical summary, no individual records | 99%+ reduction | "團隊平均健康度趨勢？" |
| **full** | Expected <5 results, need all details | No reduction | "案件 #202501-IC001 的完整資料？" |

### Decision Tree for Agents

```python
def select_context_mode(query: str, tool_def: dict) -> str:
    """
    # derived from Anthropic official doc (2025)
    Automatically select optimal context mode based on query intent.
    """

    # Statistical keywords → aggregate mode
    if any(kw in query for kw in ["平均", "趨勢", "統計", "分布", "總計"]):
        return "aggregate"

    # Specific ID/name + "詳細" → full mode
    if re.search(r"#\d+-\w+", query) and "詳細" in query:
        return "full"

    # List queries → minimal mode (default)
    if any(kw in query for kw in ["哪些", "所有", "列出", "這週", "本月"]):
        return "minimal"

    # Default: minimal (safest for context optimization)
    return "minimal"
```

---

## Real-World Optimization Examples

### Example 1: Large Dataset Query

**Query**: "過去一個月所有案件的健康度低於 60 的案件？"

**Without Optimization**:

```python
# ❌ Naive approach
raw_results = firestore.collection("cases").where("created_date", ">=", "2024-12-01").get()
# → 1000 records × 50 fields = ~250,000 tokens
# Pass all to model → context explosion
```

**With Optimization**:

```python
# ✅ Optimized approach
result = firestore_query(
    collection="cases",
    filters=[
        {"field": "created_date", "op": ">=", "value": "2024-12-01"},
        {"field": "health_score", "op": "<", "value": 60}
    ],
    context_mode="minimal"  # Filter in environment
)
# Raw: 1000 records × 50 fields = 250k tokens (in environment)
# Filtered: 50 records × 4 fields = 1k tokens (to model)
# Reduction: 99.6%
```

---

### Example 2: Aggregation Query

**Query**: "本週團隊平均健康度與上週對比？"

**Without Optimization**:

```python
# ❌ Pass all records to model for aggregation
this_week = get_cases(week="2025-W02")  # 200 records → 50k tokens
last_week = get_cases(week="2025-W01")  # 200 records → 50k tokens
# Total: 100k tokens passed to model for simple average calculation
```

**With Optimization**:

```python
# ✅ Aggregate in environment
result = firestore_query(
    collection="cases",
    filters=[{"field": "created_date", "op": ">=", "value": "2024-12-25"}],
    context_mode="aggregate"
)
# Returns:
# {
#   "avg_health_score": 75.3,
#   "by_week": {"2025-W01": 72.1, "2025-W02": 75.3},
#   "total_count": 400
# }
# Tokens: ~200 (vs. 100k)
# Reduction: 99.8%
```

---

### Example 3: Specific Record Query

**Query**: "案件 #202501-IC001 的完整資料？"

**Optimization**:

```python
# Use context_mode="full" since only 1 record expected
result = firestore_query(
    collection="cases",
    filters=[{"field": "case_id", "op": "==", "value": "202501-IC001"}],
    context_mode="full"
)
# Returns: 1 record × 50 fields = ~1,000 tokens
# This is acceptable since only 1 record
```

---

## Pre-Filtering Strategies

### Strategy 1: Field Projection

```python
# Define minimal field sets per collection
MINIMAL_FIELDS = {
    "cases": ["case_id", "customer_name", "rep_name", "health_score", "status"],
    "customers": ["customer_id", "name", "industry", "tier"],
    "reps": ["rep_id", "name", "team", "performance_score"]
}

def project_fields(records: list[dict], collection: str) -> list[dict]:
    """Keep only essential fields."""
    fields = MINIMAL_FIELDS.get(collection, [])
    return [{k: r.get(k) for k in fields} for r in records]
```

---

### Strategy 2: Smart Truncation

```python
def smart_truncate(results: list[dict], max_items: int, sort_key: str) -> list[dict]:
    """
    Truncate results intelligently by relevance.

    # derived from Anthropic official doc (2025)
    Return top N most relevant items, not just first N.
    """
    if len(results) <= max_items:
        return results

    # Sort by relevance (e.g., health_score for problem cases)
    sorted_results = sorted(results, key=lambda x: x.get(sort_key, 0))

    return sorted_results[:max_items]
```

---

### Strategy 3: PII Pre-Filtering

```python
def strip_pii_fields(record: dict) -> dict:
    """
    Remove PII fields entirely before passing to model.

    # derived from Anthropic official doc (2025)
    More aggressive than tokenization - removes fields completely.
    """
    PII_FIELDS = [
        "email", "phone", "address", "id_number",
        "credit_card", "ssn", "passport"
    ]

    return {k: v for k, v in record.items() if k not in PII_FIELDS}
```

---

## Monitoring Context Optimization

### Token Usage Tracking

```python
# src/slack_app/mcp_adapter.py

import tiktoken

class ContextOptimizationMetrics:
    """Track token savings from context optimization."""

    def __init__(self):
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def measure_optimization(
        self,
        raw_data: any,
        filtered_data: any
    ) -> dict:
        """
        Measure token reduction achieved.

        Returns:
            {
                "raw_tokens": int,
                "filtered_tokens": int,
                "reduction_pct": float,
                "effective": bool  # True if >90% reduction
            }
        """
        raw_tokens = len(self.encoder.encode(str(raw_data)))
        filtered_tokens = len(self.encoder.encode(str(filtered_data)))

        reduction_pct = (
            (raw_tokens - filtered_tokens) / raw_tokens * 100
            if raw_tokens > 0 else 0
        )

        return {
            "raw_tokens": raw_tokens,
            "filtered_tokens": filtered_tokens,
            "reduction_pct": round(reduction_pct, 2),
            "effective": reduction_pct > 90
        }
```

---

## Integration with mcp_adapter.py

The `MCPAdapter` automatically applies PII protection, but tools should implement context optimization:

```python
# Example tool with built-in optimization
def firestore_query(...):
    # Tool does field filtering + aggregation (in environment)
    filtered_data = ...

    # MCPAdapter applies PII protection on top
    return filtered_data  # Already optimized


# Usage in Agent 8
result = mcp.execute_tool("firestore.query", {
    "collection": "cases",
    "filters": [...],
    "context_mode": "minimal"  # Tool optimizes context
})
# result["result"] is both filtered AND PII-protected
```

---

## Testing Context Optimization

### Test Case: Verify Token Reduction

```python
import pytest
from mcp_adapter import MCPAdapter, ContextOptimizationMetrics

def test_context_optimization():
    mcp = MCPAdapter(session_id="test-001")
    metrics = ContextOptimizationMetrics()

    # Simulate query returning 1000 records
    result = mcp.execute_tool("firestore.query", {
        "collection": "cases",
        "filters": [{"field": "created_date", "op": ">=", "value": "2025-01-01"}],
        "context_mode": "minimal"
    })

    # Measure optimization
    # (In real test, compare against unfiltered baseline)
    optimization = metrics.measure_optimization(
        raw_data=result["_raw_data"],  # Tool would need to return this for testing
        filtered_data=result["result"]
    )

    # Assert >90% reduction
    assert optimization["reduction_pct"] > 90, \
        f"Insufficient optimization: {optimization['reduction_pct']}%"

    # Assert <5k tokens for 1000 records (minimal mode)
    assert optimization["filtered_tokens"] < 5000, \
        f"Too many tokens: {optimization['filtered_tokens']}"
```

---

**Next Steps**:

1. Update existing Firestore query code to support `context_mode` parameter
2. Implement `ContextOptimizationMetrics` for monitoring
3. Add token usage logging to all tool executions
4. Create benchmark suite to validate 90%+ reduction targets
5. Document optimization patterns for new tool developers
