# MCP Integration - Implementation Guide

**Purpose**: Step-by-step guide for implementing MCP (Model Context Protocol) integration into the sales AI automation system.

**Target Audience**: AI LLMs or human developers executing the integration.

**Source**: Derived from Anthropic official doc (2025) - <https://www.anthropic.com/engineering/code-execution-with-mcp>

**Last Updated**: 2025-11-06

---

## 📋 Overview

This guide provides complete instructions for implementing Agent 9 (MCP Integration Layer) to enable:

- 95%+ token reduction through progressive tool discovery
- 98%+ context optimization through in-environment data filtering
- Automatic PII detection and anonymization
- Secure tool execution sandbox

---

## 📂 Files Created (Reference)

All foundation files have been created. Review them before implementation:

| File | Purpose | Location |
|------|---------|----------|
| **spec.md** | MCP integration specification | `specs/001-sales-ai-automation/integration-mcp/spec.md` |
| **AGENT9_MCP_INTEGRATION.md** | Agent 9 design document | `specs/001-sales-ai-automation/AGENT9_MCP_INTEGRATION.md` |
| **mcp_adapter.py** | Core MCP adapter module | `src/slack_app/mcp_adapter.py` |
| **mcp-tool-discovery.md** | Prompt template for tool discovery | `templates/prompts/mcp-tool-discovery.md` |
| **mcp-context-optimization.md** | Prompt template for context optimization | `templates/prompts/mcp-context-optimization.md` |
| **IMPLEMENTATION_GUIDE.md** | This file | `specs/001-sales-ai-automation/integration-mcp/IMPLEMENTATION_GUIDE.md` |

---

## 🎯 Implementation Phases

### Phase 1: Setup & Verification ✅ (COMPLETED)

**Status**: Foundation files created and ready.

**Verification Steps**:

```bash
# 1. Verify all files exist
ls -la specs/001-sales-ai-automation/integration-mcp/
ls -la specs/001-sales-ai-automation/AGENT9_MCP_INTEGRATION.md
ls -la src/slack_app/mcp_adapter.py
ls -la templates/prompts/mcp-*.md

# 2. Test mcp_adapter.py module
cd src/slack_app
python mcp_adapter.py

# Expected output:
# Discovering Firestore tools...
# Found tools: []  # Empty because tools/ directory doesn't exist yet
# Loading tool definition...
# Error: No module named 'tools' (expected at this stage)
```

---

### Phase 2: Tool Infrastructure Setup 🔧 (NEXT)

**Goal**: Create tool directory structure and implement first tool.

#### Step 2.1: Create Tool Directory Structure

```bash
# Navigate to project root
cd /workspaces/sales-ai-automation-V2

# Create tool directories
mkdir -p tools/firestore
mkdir -p tools/gcs
mkdir -p tools/bigquery
mkdir -p tools/slack
mkdir -p tools/compute

# Create __init__.py files
touch tools/__init__.py
touch tools/firestore/__init__.py
touch tools/gcs/__init__.py
touch tools/bigquery/__init__.py
touch tools/slack/__init__.py
touch tools/compute/__init__.py
```

#### Step 2.2: Implement First Tool - `firestore.query`

**File**: `tools/firestore/query.py`

**Template**:

```python
"""
Tool: firestore_query
Category: firestore
Version: 1.0.0
Description: Query Firestore with automatic context optimization and PII protection

# derived from Anthropic official doc (2025)
"""

from google.cloud import firestore
from typing import List, Dict, Any, Optional


def query(
    collection: str,
    filters: List[Dict[str, Any]],
    order_by: Optional[str] = None,
    limit: int = 100,
    context_mode: str = "minimal"
) -> Dict[str, Any]:
    """
    Query Firestore collection with automatic context optimization.

    Args:
        collection: Collection name (e.g., "cases", "customers")
        filters: List of filter dicts with structure:
                 [{"field": str, "op": str, "value": Any}]
                 Operators: "==", "!=", "<", "<=", ">", ">=", "in", "array-contains"
        order_by: Field name for sorting (optional)
        limit: Maximum number of results to return
        context_mode: "minimal" | "full" | "aggregate"
            - minimal: Return only essential fields (default, 96-98% token reduction)
            - full: Return all fields (use only for <10 results)
            - aggregate: Return statistics only (99%+ token reduction)

    Returns:
        {
            "results": List[Dict] or Dict (for aggregate mode),
            "total_count": int,
            "returned_count": int,
            "truncated": bool,
            "context_mode": str
        }

    Example:
        result = query(
            collection="cases",
            filters=[
                {"field": "rep_name", "op": "==", "value": "王小明"},
                {"field": "health_score", "op": "<", "value": 60}
            ],
            order_by="health_score",
            limit=50,
            context_mode="minimal"
        )
    """

    # =====================================
    # STAGE 1: QUERY EXECUTION (in environment)
    # =====================================
    # Initialize Firestore client (reuse existing client if available)
    db = firestore.Client()
    query_ref = db.collection(collection)

    # Apply filters
    for f in filters:
        query_ref = query_ref.where(f["field"], f["op"], f["value"])

    # Apply ordering
    if order_by:
        query_ref = query_ref.order_by(order_by)

    # Fetch results (fetch extra for potential filtering)
    raw_results = list(query_ref.limit(limit * 2).stream())

    # Convert to dicts
    raw_data = [doc.to_dict() for doc in raw_results]

    # =====================================
    # STAGE 2: FIELD FILTERING (in environment)
    # derived from Anthropic official doc (2025)
    # =====================================
    if context_mode == "minimal":
        # Define essential fields per collection
        MINIMAL_FIELDS = {
            "cases": ["case_id", "customer_name", "rep_name", "health_score",
                     "created_date", "status"],
            "customers": ["customer_id", "name", "industry", "tier"],
            "reps": ["rep_id", "name", "team", "performance_score"],
        }

        essential_fields = MINIMAL_FIELDS.get(collection,
                                              ["id", "name", "created_date", "status"])

        filtered_results = [
            {k: doc.get(k) for k in essential_fields if k in doc}
            for doc in raw_data
        ]

    elif context_mode == "aggregate":
        # Compute aggregations in environment
        import pandas as pd

        if not raw_data:
            return {
                "results": {"total_count": 0},
                "total_count": 0,
                "returned_count": 0,
                "truncated": False,
                "context_mode": "aggregate"
            }

        df = pd.DataFrame(raw_data)

        # Compute common statistics
        filtered_results = {
            "total_count": len(df),
            "avg_health_score": float(df["health_score"].mean()) if "health_score" in df else None,
            "median_health_score": float(df["health_score"].median()) if "health_score" in df else None,
            "min_health_score": float(df["health_score"].min()) if "health_score" in df else None,
            "max_health_score": float(df["health_score"].max()) if "health_score" in df else None,
        }

        # Group by rep_name if exists
        if "rep_name" in df:
            filtered_results["by_rep"] = df.groupby("rep_name")["health_score"].agg(
                ["mean", "count"]
            ).to_dict()

        # Group by status if exists
        if "status" in df:
            filtered_results["by_status"] = df["status"].value_counts().to_dict()

    else:  # context_mode == "full"
        filtered_results = raw_data

    # =====================================
    # STAGE 3: RESULT TRUNCATION (in environment)
    # =====================================
    if context_mode != "aggregate" and len(filtered_results) > limit:
        filtered_results = filtered_results[:limit]

    # =====================================
    # STAGE 4: RETURN TO MODEL
    # =====================================
    return {
        "results": filtered_results,
        "total_count": len(raw_data),
        "returned_count": len(filtered_results) if context_mode != "aggregate" else 1,
        "truncated": len(raw_data) > limit,
        "context_mode": context_mode
    }
```

**Verification**:

```bash
# Test the tool
cd /workspaces/sales-ai-automation-V2
python -c "
from tools.firestore.query import query

# This will fail if Firestore not configured, but validates import
try:
    result = query(
        collection='cases',
        filters=[{'field': 'rep_name', 'op': '==', 'value': '測試'}],
        limit=10,
        context_mode='minimal'
    )
    print('Tool import successful')
except Exception as e:
    print(f'Expected error (Firestore not configured): {e}')
"
```

---

### Phase 3: MCP Adapter Integration 🔌 (NEXT)

**Goal**: Integrate MCP adapter with existing Agent 8 handler.

#### Step 3.1: Update Agent 8 Handler

**File**: `src/slack_app/handlers/agent8_handler.py`

**Add MCP Import**:

```python
# Add to imports at top of file
from mcp_adapter import MCPAdapter
```

**Add MCP Initialization**:

```python
class Agent8Handler:
    def __init__(self):
        self.gemini_client = None  # Existing
        self.mcp = None  # NEW: MCP adapter (initialized per session)

    async def handle_user_query(self, user_query: str, session_id: str, user_id: str):
        """
        Handle user query with MCP tool support.
        """
        # Initialize MCP adapter for this session
        if self.mcp is None or self.mcp.session_id != session_id:
            self.mcp = MCPAdapter(
                session_id=session_id,
                tools_dir="tools",
                enable_pii_protection=True
            )

        # Infer if query requires data access
        needs_tools = self._needs_tools(user_query)

        if needs_tools:
            # Progressive tool discovery
            category = self._infer_tool_category(user_query)
            tools = self.mcp.discover_tools(category=category, detail_level="names")

            # Tool selection (can use LLM to select best tool)
            selected_tool = self._select_tool(tools, user_query)

            # Load tool definition
            tool_def = self.mcp.load_tool(selected_tool)

            # Construct parameters (can use LLM to extract from query)
            params = self._construct_tool_params(user_query, tool_def)

            # Execute tool with context optimization
            result = self.mcp.execute_tool(selected_tool, params, timeout=30)

            # Generate response based on tool result
            if result["status"] == "success":
                answer = self._generate_answer_with_data(user_query, result["result"])
            else:
                answer = f"抱歉，查詢資料時發生錯誤：{result.get('error', 'Unknown error')}"

            return answer
        else:
            # Direct LLM response (existing logic)
            return await self._direct_gemini_response(user_query)

    def _needs_tools(self, query: str) -> bool:
        """Check if query requires data access tools."""
        # Simple keyword matching (can be enhanced with LLM classification)
        data_keywords = ["案件", "資料", "統計", "健康度", "客戶", "業務員", "團隊"]
        return any(kw in query for kw in data_keywords)

    def _infer_tool_category(self, query: str) -> str:
        """Infer required tool category from query."""
        if any(kw in query for kw in ["案件", "客戶", "業務員", "健康度"]):
            return "firestore"
        elif any(kw in query for kw in ["檔案", "上傳", "下載"]):
            return "gcs"
        elif any(kw in query for kw in ["SQL", "分析", "報表"]):
            return "bigquery"
        else:
            return "firestore"  # Default

    def _select_tool(self, tools: List[str], query: str) -> str:
        """Select most appropriate tool."""
        # Simple selection (can be enhanced with LLM reasoning)
        if "統計" in query or "平均" in query or "趨勢" in query:
            # Prefer aggregate tools
            for tool in tools:
                if "aggregate" in tool:
                    return tool

        # Default to first query tool
        for tool in tools:
            if "query" in tool:
                return tool

        return tools[0] if tools else "firestore.query"

    def _construct_tool_params(self, query: str, tool_def: dict) -> dict:
        """Construct tool parameters from query."""
        # TODO: Use LLM to extract entities and construct params
        # For now, return basic structure

        params = {
            "collection": "cases",  # Extract from query
            "filters": [],  # Extract from query
            "limit": 100,
            "context_mode": "minimal"  # Use minimal by default for token optimization
        }

        # Extract rep name if mentioned
        import re
        name_match = re.search(r"([\u4e00-\u9fff]{2,4})", query)
        if name_match:
            rep_name = name_match.group(1)
            params["filters"].append({
                "field": "rep_name",
                "op": "==",
                "value": rep_name
            })

        # Check if aggregate mode needed
        if any(kw in query for kw in ["平均", "統計", "趨勢", "分布"]):
            params["context_mode"] = "aggregate"

        return params

    def _generate_answer_with_data(self, query: str, data: Any) -> str:
        """Generate natural language answer based on query and data."""
        # TODO: Use Gemini to generate response
        # For now, return simple formatted response

        if isinstance(data, dict) and "results" in data:
            results = data["results"]
            if isinstance(results, list):
                return f"查詢結果：共找到 {len(results)} 筆資料\n{results[:3]}"  # Show first 3
            else:
                return f"統計結果：\n{results}"
        else:
            return str(data)
```

---

### Phase 4: Testing & Validation ✅ (NEXT)

**Goal**: Verify MCP integration works end-to-end.

#### Step 4.1: Unit Tests

**File**: `tests/unit/test_mcp_adapter.py`

```python
"""
Unit tests for MCP Adapter.
"""

import pytest
from src.slack_app.mcp_adapter import MCPAdapter, PIIAnonymizer, ToolRegistry


class TestPIIAnonymizer:
    def test_email_anonymization(self):
        anonymizer = PIIAnonymizer(session_id="test-001")

        data = {"email": "test@example.com", "name": "John"}
        result = anonymizer.anonymize(data)

        assert result["email"].startswith("[EMAIL_")
        assert result["name"] == "John"
        assert "test@example.com" in anonymizer.pii_map["email"].values()

    def test_phone_anonymization(self):
        anonymizer = PIIAnonymizer(session_id="test-002")

        data = {"phone": "0912-345-678"}
        result = anonymizer.anonymize(data)

        assert result["phone"].startswith("[PHONE_")

    def test_nested_anonymization(self):
        anonymizer = PIIAnonymizer(session_id="test-003")

        data = {
            "users": [
                {"email": "user1@test.com"},
                {"email": "user2@test.com"}
            ]
        }
        result = anonymizer.anonymize(data)

        assert result["users"][0]["email"].startswith("[EMAIL_")
        assert result["users"][1]["email"].startswith("[EMAIL_")
        assert len(anonymizer.pii_map["email"]) == 2


class TestToolRegistry:
    def test_discover_tools_names_only(self):
        registry = ToolRegistry(tools_dir="tools")

        # Should return list of tool names
        tools = registry.discover_tools(category="firestore", detail_level="names")

        assert isinstance(tools, list)
        # Will be empty until tools are created
        # assert "firestore.query" in tools  # Uncomment after Phase 2

    def test_load_tool_definition(self):
        registry = ToolRegistry(tools_dir="tools")

        # Should cache tool definition
        # tool_def = registry.load_tool("firestore.query")  # Uncomment after Phase 2
        # assert "name" in tool_def
        # assert "description" in tool_def
        # assert "parameters" in tool_def


class TestMCPAdapter:
    def test_initialization(self):
        mcp = MCPAdapter(session_id="test-session-001")

        assert mcp.session_id == "test-session-001"
        assert mcp.registry is not None
        assert mcp.executor is not None
        assert mcp.anonymizer is not None

    def test_get_session_stats(self):
        mcp = MCPAdapter(session_id="test-session-002")

        stats = mcp.get_session_stats()

        assert stats["session_id"] == "test-session-002"
        assert "cached_tools" in stats
        assert "pii_detections" in stats
```

**Run Tests**:

```bash
cd /workspaces/sales-ai-automation-V2
pytest tests/unit/test_mcp_adapter.py -v
```

#### Step 4.2: Integration Tests

**File**: `tests/integration/test_mcp_firestore_integration.py`

```python
"""
Integration tests for MCP + Firestore tool.
"""

import pytest
from src.slack_app.mcp_adapter import MCPAdapter


@pytest.mark.integration
class TestFirestoreToolIntegration:
    def test_firestore_query_minimal_mode(self):
        """Test that minimal mode reduces tokens significantly."""
        mcp = MCPAdapter(session_id="integration-test-001")

        # Execute query with minimal mode
        result = mcp.execute_tool("firestore.query", {
            "collection": "cases",
            "filters": [
                {"field": "created_date", "op": ">=", "value": "2025-01-01"}
            ],
            "limit": 100,
            "context_mode": "minimal"
        })

        assert result["status"] == "success"

        # Verify only essential fields returned
        if result["result"]["returned_count"] > 0:
            first_record = result["result"]["results"][0]
            assert "case_id" in first_record
            assert "health_score" in first_record
            # Should NOT have all 50 fields
            assert len(first_record.keys()) <= 10

    def test_firestore_query_aggregate_mode(self):
        """Test that aggregate mode returns statistics only."""
        mcp = MCPAdapter(session_id="integration-test-002")

        result = mcp.execute_tool("firestore.query", {
            "collection": "cases",
            "filters": [],
            "limit": 1000,
            "context_mode": "aggregate"
        })

        assert result["status"] == "success"

        # Verify statistics returned
        stats = result["result"]["results"]
        assert "total_count" in stats
        assert "avg_health_score" in stats
        # No individual records
        assert not isinstance(stats, list)

    def test_pii_protection(self):
        """Test that PII is automatically anonymized."""
        mcp = MCPAdapter(session_id="integration-test-003")

        # Mock result with PII
        result = mcp.execute_tool("firestore.query", {
            "collection": "customers",
            "filters": [{"field": "tier", "op": "==", "value": "premium"}],
            "limit": 10,
            "context_mode": "full"
        })

        # Check that emails are tokenized
        if result["status"] == "success":
            for record in result["result"]["results"]:
                if "email" in record:
                    # Should be [EMAIL_N] format
                    assert record["email"].startswith("[EMAIL_") or "@" not in record["email"]
```

**Run Integration Tests**:

```bash
# Requires Firestore to be configured
pytest tests/integration/test_mcp_firestore_integration.py -v -m integration
```

---

### Phase 5: Monitoring & Optimization 📊 (FUTURE)

**Goal**: Track token usage and validate optimization targets.

#### Step 5.1: Token Usage Monitoring

**File**: `src/slack_app/monitoring/token_tracker.py`

```python
"""
Token usage monitoring for MCP optimization validation.

# derived from Anthropic official doc (2025)
"""

import tiktoken
from datetime import datetime
from typing import Dict, Any


class TokenUsageTracker:
    """Track token savings from MCP optimization."""

    def __init__(self):
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.metrics = []

    def measure_optimization(
        self,
        tool_name: str,
        raw_data_size: int,
        filtered_data: Any,
        context_mode: str
    ) -> Dict[str, Any]:
        """
        Measure token reduction achieved.

        Args:
            tool_name: Tool identifier
            raw_data_size: Number of raw records returned
            filtered_data: Filtered data passed to model
            context_mode: Context mode used

        Returns:
            Optimization metrics
        """
        # Estimate raw tokens (assuming 50 fields per record)
        estimated_raw_tokens = raw_data_size * 50 * 10  # ~500 tokens per record

        # Measure actual filtered tokens
        filtered_tokens = len(self.encoder.encode(str(filtered_data)))

        # Calculate reduction
        reduction_pct = (
            (estimated_raw_tokens - filtered_tokens) / estimated_raw_tokens * 100
            if estimated_raw_tokens > 0 else 0
        )

        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool_name": tool_name,
            "context_mode": context_mode,
            "raw_records": raw_data_size,
            "estimated_raw_tokens": estimated_raw_tokens,
            "filtered_tokens": filtered_tokens,
            "reduction_pct": round(reduction_pct, 2),
            "target_met": reduction_pct >= 90  # Target: 90%+ reduction
        }

        self.metrics.append(metric)
        return metric

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self.metrics:
            return {"total_measurements": 0}

        total_raw = sum(m["estimated_raw_tokens"] for m in self.metrics)
        total_filtered = sum(m["filtered_tokens"] for m in self.metrics)
        avg_reduction = sum(m["reduction_pct"] for m in self.metrics) / len(self.metrics)
        target_met_count = sum(1 for m in self.metrics if m["target_met"])

        return {
            "total_measurements": len(self.metrics),
            "total_raw_tokens": total_raw,
            "total_filtered_tokens": total_filtered,
            "overall_reduction_pct": round((total_raw - total_filtered) / total_raw * 100, 2),
            "avg_reduction_pct": round(avg_reduction, 2),
            "target_met_pct": round(target_met_count / len(self.metrics) * 100, 2),
            "by_context_mode": self._group_by_context_mode()
        }

    def _group_by_context_mode(self) -> Dict[str, Dict]:
        """Group metrics by context mode."""
        grouped = {}
        for metric in self.metrics:
            mode = metric["context_mode"]
            if mode not in grouped:
                grouped[mode] = []
            grouped[mode].append(metric)

        return {
            mode: {
                "count": len(metrics),
                "avg_reduction": round(
                    sum(m["reduction_pct"] for m in metrics) / len(metrics), 2
                )
            }
            for mode, metrics in grouped.items()
        }
```

**Integration with MCP Adapter**:

```python
# Add to MCPAdapter class in mcp_adapter.py

from monitoring.token_tracker import TokenUsageTracker

class MCPAdapter:
    def __init__(self, session_id: str, ...):
        # ... existing code ...
        self.token_tracker = TokenUsageTracker()

    def execute_tool(self, tool_name: str, params: Dict[str, Any], ...) -> Dict[str, Any]:
        # ... existing execution code ...

        # Track token usage
        if result["status"] == "success" and "total_count" in result["result"]:
            metric = self.token_tracker.measure_optimization(
                tool_name=tool_name,
                raw_data_size=result["result"]["total_count"],
                filtered_data=result["result"]["results"],
                context_mode=params.get("context_mode", "minimal")
            )
            result["token_optimization"] = metric

        return result
```

---

## 🎯 Success Criteria

### Phase 2 Complete When

- [ ] `tools/` directory structure created
- [ ] `tools/firestore/query.py` implemented and tested
- [ ] Tool can be imported without errors
- [ ] Tool supports all 3 context modes (minimal/full/aggregate)

### Phase 3 Complete When

- [ ] `agent8_handler.py` updated with MCP integration
- [ ] Agent 8 can discover tools via MCP
- [ ] Agent 8 can execute tools and get results
- [ ] PII is automatically anonymized in results

### Phase 4 Complete When

- [ ] Unit tests pass (85%+ coverage for mcp_adapter.py)
- [ ] Integration tests pass (requires Firestore connection)
- [ ] Manual e2e test: User query → Tool execution → Response

### Phase 5 Complete When

- [ ] Token tracking enabled for all tool calls
- [ ] 90%+ optimization rate achieved for minimal mode
- [ ] 98%+ optimization rate achieved for aggregate mode
- [ ] Dashboard/logs show token savings metrics

---

## 🚀 Quick Start Commands

### For Another LLM to Execute

```bash
# Phase 2: Setup tools
cd /workspaces/sales-ai-automation-V2

# Create directories
mkdir -p tools/{firestore,gcs,bigquery,slack,compute}
touch tools/__init__.py tools/firestore/__init__.py

# Create first tool (copy template from Step 2.2 above)
# File: tools/firestore/query.py

# Phase 3: Update Agent 8
# Edit: src/slack_app/handlers/agent8_handler.py
# Add MCP integration code from Step 3.1

# Phase 4: Run tests
pytest tests/unit/test_mcp_adapter.py -v
pytest tests/integration/ -v -m integration

# Phase 5: Monitor optimization
# Check token savings in logs/metrics
```

---

## 📚 Reference Documents

Read these before implementing:

1. **spec.md** - Full specification with acceptance criteria
2. **AGENT9_MCP_INTEGRATION.md** - Agent 9 design and architecture
3. **mcp-tool-discovery.md** - How to implement progressive disclosure
4. **mcp-context-optimization.md** - How to achieve 98%+ token reduction

---

## 🔧 Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'tools'`

**Solution**: Ensure `tools/` directory exists and has `__init__.py`

### Issue: Firestore connection errors

**Solution**: Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

### Issue: Tool execution timeout

**Solution**: Increase timeout parameter in `execute_tool()` call

### Issue: PII not anonymized

**Solution**: Verify `enable_pii_protection=True` in MCPAdapter initialization

---

## 📝 Notes for Executing LLM

**Important Reminders**:

1. **All foundation files already exist** - Review them first before implementing
2. **Follow phases sequentially** - Phase 2 must complete before Phase 3
3. **Test after each phase** - Don't proceed if tests fail
4. **Token optimization is critical** - Target 90%+ reduction for success
5. **PII protection is mandatory** - Never pass raw PII to model

**What to Ask User**:

- "Do you have Firestore credentials configured?" (needed for Phase 4 testing)
- "Should I proceed with Phase 2 (Tool Infrastructure Setup)?" (next step)
- "Do you want to implement additional tools beyond firestore.query?" (expansion)

---

**Last Updated**: 2025-11-06
**Status**: Ready for Phase 2 implementation
