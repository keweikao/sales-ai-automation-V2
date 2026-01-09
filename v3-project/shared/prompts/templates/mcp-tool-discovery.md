# MCP Tool Discovery Prompt Template

**Purpose**: Guide AI agents to efficiently discover and select tools using progressive disclosure strategy.

**Source**: Derived from Anthropic official doc (2025) - <https://www.anthropic.com/engineering/code-execution-with-mcp>

**Token Optimization**: This prompt reduces context usage by 95%+ through progressive tool loading.

---

## Phase 1: Minimal Tool Discovery (10 tokens/tool)

### System Instruction

```
You are an AI agent with access to external tools via the MCP (Model Context Protocol) integration layer.

# derived from Anthropic official doc (2025)
IMPORTANT: Do NOT load all tool definitions at once. Use progressive disclosure:
1. First, discover tool NAMES only (minimal context)
2. Select relevant tool based on user query
3. Load FULL definition only for selected tool

Tool categories available:
- firestore: Query Firestore database
- gcs: Google Cloud Storage operations
- bigquery: BigQuery SQL queries
- slack: Send Slack messages
- compute: Statistical computations

Current user query requires: {INFERRED_CATEGORY}
```

### Agent Action Template

```python
# Step 1: Discover tool names only (minimal context)
tools = mcp.discover_tools(
    category="{INFERRED_CATEGORY}",  # e.g., "firestore"
    detail_level="names"  # Only tool names, ~10 tokens/tool
)
# Example result: ["firestore.query", "firestore.aggregate", "firestore.list_collections"]

# Step 2: Select most relevant tool (agent reasoning)
selected_tool = self._select_tool_by_intent(tools, user_query)
# → "firestore.query"

# Step 3: Load ONLY the selected tool's full definition
tool_def = mcp.load_tool(selected_tool)
# This step loads ~200 tokens (vs. 10,000+ if loading all tools)
```

---

## Phase 2: Tool Selection Reasoning

### Prompt for Agent

```
Based on user query: "{USER_QUERY}"
Available tools in category '{CATEGORY}': {TOOL_NAMES_LIST}

Select the most appropriate tool by reasoning:
1. What data/action does the query require?
2. Which tool best matches this requirement?
3. Are there any alternative tools to consider?

Output format:
{
  "selected_tool": "category.tool_name",
  "reasoning": "Brief explanation of why this tool fits",
  "confidence": 0.0-1.0
}

Example:
User query: "王小明這週的案件健康度如何？"
Available tools: ["firestore.query", "firestore.aggregate"]

Output:
{
  "selected_tool": "firestore.query",
  "reasoning": "需要查詢特定業務員的案件資料，需要過濾條件（rep_name、日期範圍），query 工具提供完整篩選能力",
  "confidence": 0.95
}
```

---

## Phase 3: Parameter Construction

### Prompt for Agent

```
You have selected tool: {TOOL_NAME}

Tool definition:
{TOOL_FULL_DEFINITION}

User query: {USER_QUERY}

Construct tool parameters:
1. Extract entities from user query (person names, dates, metrics)
2. Map to tool parameters (collection, filters, limit)
3. Set context_mode appropriately:
   - "minimal": For queries expecting 10+ results (default)
   - "full": For queries expecting <5 results
   - "aggregate": For statistical summaries

# derived from Anthropic official doc (2025)
CRITICAL: Always use context_mode="minimal" for large result sets to achieve
98%+ token reduction through in-environment filtering.

Output format:
{
  "tool_name": "...",
  "parameters": { ... },
  "expected_result_size": "small"|"medium"|"large",
  "context_mode": "minimal"|"full"|"aggregate"
}
```

---

## Complete Workflow Example

### User Query

"王小明這週的案件健康度如何？哪些案件需要關注？"

### Agent Reasoning Process

```
Step 1: Infer required category
→ 需要查詢資料：category = "firestore"

Step 2: Discover tools (minimal)
tools = mcp.discover_tools(category="firestore", detail_level="names")
→ ["firestore.query", "firestore.aggregate", "firestore.list_collections"]
(Cost: ~30 tokens, vs. 10,000+ if loading all 50 tools)

Step 3: Select tool
Query requires: 篩選特定業務員 + 日期範圍 + 健康度指標
→ selected_tool = "firestore.query"

Step 4: Load full definition
tool_def = mcp.load_tool("firestore.query")
→ 200 tokens (parameters, examples, description)

Step 5: Construct parameters
{
  "tool_name": "firestore.query",
  "parameters": {
    "collection": "cases",
    "filters": [
      {"field": "rep_name", "op": "==", "value": "王小明"},
      {"field": "created_date", "op": ">=", "value": "2025-11-01"},
      {"field": "created_date", "op": "<=", "value": "2025-11-07"}
    ],
    "order_by": "health_score",
    "limit": 100,
    "context_mode": "minimal"  # Auto-filter to essential fields
  },
  "expected_result_size": "medium",
  "context_mode": "minimal"
}

Step 6: Execute tool
result = mcp.execute_tool("firestore.query", parameters)
→ Raw data: 100 cases × 50 fields = ~50,000 tokens
→ After context_mode="minimal" filtering: 100 cases × 4 fields = ~2,000 tokens
→ Token savings: 96%
```

---

## Token Optimization Summary

| Approach | Tokens Used | Description |
|----------|-------------|-------------|
| **Naive (load all tools)** | 10,000+ | Pre-load 50 tools × 200 tokens |
| **Progressive Disclosure** | 230 | 30 (discovery) + 200 (one tool definition) |
| **Savings** | **97.7%** | Critical for context efficiency |

---

## Best Practices

### ✅ DO

1. **Always start with minimal discovery** (`detail_level="names"`)
2. **Load full definitions only for selected tools**
3. **Use context_mode="minimal"** for expected large result sets
4. **Cache tool definitions** within same session (automatic in `mcp_adapter.py`)
5. **Reason explicitly** about tool selection before loading

### ❌ DON'T

1. **Never load all tools at initialization** (context explosion)
2. **Don't use context_mode="full"** for 100+ results (token waste)
3. **Don't skip tool selection reasoning** (leads to wrong tool choice)
4. **Don't load tool definitions "just in case"** (violates progressive disclosure)

---

## Integration with Agent 8

### Agent 8 Handler Modification

```python
# src/slack_app/handlers/agent8_handler.py

from mcp_adapter import MCPAdapter

class Agent8Handler:
    def __init__(self):
        self.mcp = None  # Initialized per session

    async def handle_user_query(self, user_query: str, session_id: str):
        # Initialize MCP adapter for this session
        self.mcp = MCPAdapter(session_id=session_id)

        # Infer required tool category
        category = self._infer_category(user_query)

        if category:
            # Progressive tool discovery
            tools = self.mcp.discover_tools(
                category=category,
                detail_level="names"
            )

            # Tool selection reasoning
            selected_tool = self._select_tool(tools, user_query)

            # Load full definition
            tool_def = self.mcp.load_tool(selected_tool)

            # Construct parameters
            params = self._construct_params(user_query, tool_def)

            # Execute with context optimization
            result = self.mcp.execute_tool(selected_tool, params)

            # Generate response based on filtered result
            answer = self._generate_answer(user_query, result)
            return answer
        else:
            # No tool required, direct LLM response
            return self._direct_llm_response(user_query)
```

---

## Testing Progressive Disclosure

### Test Case 1: Token Usage Measurement

```python
import tiktoken

# Scenario: Query requiring Firestore tool
user_query = "王小明這週的案件？"

# Method A: Naive (load all tools)
all_tools = load_all_tool_definitions()  # 50 tools
encoder = tiktoken.get_encoding("cl100k_base")
tokens_naive = len(encoder.encode(str(all_tools)))
# → ~10,000 tokens

# Method B: Progressive Disclosure
tools_names = mcp.discover_tools(category="firestore", detail_level="names")
selected_tool_def = mcp.load_tool("firestore.query")
encoder = tiktoken.get_encoding("cl100k_base")
tokens_progressive = len(encoder.encode(str(tools_names) + str(selected_tool_def)))
# → ~230 tokens

savings = (tokens_naive - tokens_progressive) / tokens_naive * 100
print(f"Token savings: {savings:.1f}%")  # → 97.7%
```

### Test Case 2: End-to-End Query

```python
# User query with expected large result set
query = "過去一個月所有案件的健康度分布？"

# Execute with progressive disclosure + context optimization
result = agent8.handle_user_query(query, session_id="test-001")

# Verify token reduction
# Expected:
# - Raw data: 1000 cases × 50 fields = ~250,000 tokens
# - After optimization: ~3,000 tokens (aggregate stats only)
# - Reduction: 98.8%
```

---

**Next Steps**:

1. Integrate this prompt template into Agent 8 system prompt
2. Implement `_infer_category()`, `_select_tool()`, `_construct_params()` helper methods
3. Add token usage monitoring to track optimization effectiveness
4. Create test suite for progressive disclosure scenarios
