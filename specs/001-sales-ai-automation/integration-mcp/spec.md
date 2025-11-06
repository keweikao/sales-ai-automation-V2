# Feature Specification: MCP Integration for Agent Tooling

**Feature Branch**: `001-sales-ai-automation/integration-mcp`
**Created**: 2025-11-06
**Status**: Draft
**Source**: Derived from Anthropic official doc (2025) - https://www.anthropic.com/engineering/code-execution-with-mcp

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Progressive Tool Discovery (Priority: P1)

**As a** AI agent (Agent 8 Conversational or future agents)
**I want to** discover and load tool definitions on-demand rather than loading all tools at initialization
**So that** I can reduce context token usage by 95%+ and avoid overwhelming the model with unnecessary tool definitions

**Why this priority**: Context window efficiency is critical for cost optimization and performance. Loading all tool definitions upfront wastes tokens and degrades response quality. Progressive disclosure is the foundation for scalable tool integration.

**Independent Test**: Agent requests a tool for "Firestore query". System should discover the tool definition only when requested, load it dynamically, and execute without pre-loading other unrelated tools (e.g., GCS, BigQuery tools).

**Acceptance Scenarios**:

- **Given** an agent needs to query Firestore for case data
  **When** agent invokes tool discovery with intent "query firestore"
  **Then** system should:
  - Search tool registry by keyword/intent match
  - Return only relevant tool definitions (e.g., `firestore_query`, `firestore_list_collections`)
  - NOT load unrelated tools (e.g., BigQuery, GCS tools)
  - Complete discovery in <500ms
  - Reduce context usage to <2000 tokens (vs. 150k+ if loading all tools)

- **Given** agent requires a tool not yet in cache
  **When** tool is requested by name or description
  **Then** system should:
  - Fetch tool definition from tool registry (file-based or API)
  - Parse tool schema (parameters, description, examples)
  - Cache for subsequent invocations
  - Return formatted tool definition to agent

- **Given** agent makes repeated calls to the same tool
  **When** tool definition is already cached
  **Then** system should:
  - Return cached definition without re-fetching
  - Maintain cache for session duration
  - Clear cache on session end or manual invalidation

---

### User Story 2 - In-Environment Data Filtering (Priority: P1)

**As a** AI agent processing large datasets (e.g., 10k+ Firestore documents)
**I want to** filter and transform data within the execution environment before passing results to the model
**So that** only relevant, summarized data enters the model context, achieving 98%+ token reduction

**Why this priority**: Data filtering is the primary mechanism for context optimization. Without it, large query results overwhelm the model, causing quality degradation and cost explosion (e.g., 150k tokens → 2k tokens as demonstrated in Anthropic's case study).

**Independent Test**: Query returns 5000 case records. System filters to 10 high-priority cases based on health_score, returns only essential fields (case_id, health_score, customer_name), reducing context from ~100k to ~1k tokens.

**Acceptance Scenarios**:

- **Given** a Firestore query returns 5000 case documents
  **When** agent specifies filter criteria (e.g., "health_score < 60", "created_date > 7 days ago")
  **Then** system should:
  - Execute filter logic in Python execution environment
  - Apply criteria without passing raw data to model
  - Return only matching records (e.g., 10 critical cases)
  - Strip unnecessary fields (keep only case_id, health_score, customer_name, rep_name)
  - Achieve token reduction ratio >95% (e.g., 100k → 3k tokens)

- **Given** agent needs aggregated statistics (e.g., "average health score by rep")
  **When** raw data exceeds 1000 records
  **Then** system should:
  - Compute aggregations in execution environment (pandas, numpy)
  - Return only summary statistics (mean, median, count per group)
  - NOT pass individual records to model
  - Complete computation in <3 seconds

- **Given** sensitive PII exists in query results (e.g., phone numbers, emails)
  **When** data is prepared for model context
  **Then** system should:
  - Auto-detect PII patterns (regex-based: phone, email, ID numbers)
  - Tokenize PII as `[EMAIL_1]`, `[PHONE_2]`, etc.
  - Store mapping in secure session storage
  - Pass only tokenized data to model
  - Restore original values only when necessary for final output

---

### User Story 3 - Tool Organization & Discoverability (Priority: P2)

**As a** system administrator
**I want to** organize MCP tools in a hierarchical file/directory structure
**So that** agents can explore available tools programmatically and humans can maintain tool definitions easily

**Why this priority**: Scalability and maintainability require structured tool organization. File-based structure enables version control, code review, and easy addition of new tools without code changes.

**Independent Test**: Add a new tool `bigquery_query.py` to `tools/bigquery/` directory. Agent should discover it automatically without redeployment, load its definition on-demand, and execute successfully.

**Acceptance Scenarios**:

- **Given** tools are organized in directory structure:
  ```
  tools/
  ├── firestore/
  │   ├── query.py
  │   ├── list_collections.py
  ├── gcs/
  │   ├── upload.py
  │   ├── download.py
  ├── bigquery/
      ├── query.py
  ```
  **When** agent requests tool list for "firestore" category
  **Then** system should:
  - Scan `tools/firestore/` directory
  - Return list of available tools with brief descriptions
  - NOT load full tool schemas (only names + one-line descriptions)
  - Support filtering by category, keyword, tags

- **Given** a new tool is added to `tools/slack/send_message.py`
  **When** agent queries "send slack notification"
  **Then** system should:
  - Auto-discover new tool via file scan or manifest update
  - Parse tool metadata (docstring, type hints)
  - Make tool available without service restart
  - Log tool registration event

---

### User Story 4 - Secure Execution Sandbox (Priority: P2)

**As a** system operator
**I want to** execute tool code in a secure sandbox with resource limits
**So that** untrusted or buggy tool code cannot compromise system stability or security

**Why this priority**: Security and reliability are foundational. Tools may have bugs, infinite loops, or malicious code. Sandboxing prevents system-wide failures.

**Independent Test**: Deploy a buggy tool with infinite loop. System should terminate execution after 30s timeout, return error to agent, and remain stable for subsequent tool calls.

**Acceptance Scenarios**:

- **Given** a tool execution is initiated
  **When** tool code runs
  **Then** system should:
  - Execute in isolated Python process/container
  - Apply CPU timeout (default: 30s, configurable per tool)
  - Apply memory limit (default: 512MB, configurable)
  - Restrict file system access (read-only except temp directory)
  - Block network access unless explicitly whitelisted for tool
  - Capture stdout/stderr separately from result

- **Given** a tool exceeds timeout (30s)
  **When** timeout is reached
  **Then** system should:
  - Forcefully terminate tool process (SIGKILL)
  - Return error to agent: "Tool execution timeout after 30s"
  - Log incident with tool name, parameters, duration
  - NOT crash main service
  - Allow subsequent tool calls to proceed normally

- **Given** a tool attempts unauthorized file access (e.g., `/etc/passwd`)
  **When** file operation is attempted
  **Then** system should:
  - Block operation with PermissionError
  - Log security violation
  - Return error to agent
  - Consider tool as untrusted (flag for review)

---

### Edge Cases

- **What happens when** tool discovery returns no matches for agent's query?
  → System should suggest similar tools (fuzzy match) or return "No tools found" with guidance to refine query.

- **How does system handle** tool definition parsing errors (e.g., invalid JSON schema)?
  → Log error, skip tool, continue with other tools. Return warning to agent if requested tool is unavailable.

- **What happens when** multiple tools match the same query (e.g., "query database")?
  → Return all matches with detailed descriptions. Let agent or user select appropriate tool. Optionally rank by relevance score.

- **How does system handle** tool version conflicts (e.g., `firestore_query_v1` vs `firestore_query_v2`)?
  → Use semantic versioning. Default to latest stable version. Allow explicit version selection in tool call.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support on-demand tool discovery by keyword, category, or intent description
- **FR-002**: System MUST load tool definitions dynamically without requiring service restart
- **FR-003**: System MUST filter query results in execution environment before passing to model context
- **FR-004**: System MUST achieve >90% token reduction for large dataset queries (benchmark: 10k+ records)
- **FR-005**: System MUST auto-detect and tokenize PII in query results (email, phone, ID numbers)
- **FR-006**: System MUST organize tools in hierarchical directory structure (`tools/category/tool_name.py`)
- **FR-007**: System MUST execute tool code in sandboxed environment with timeout (30s default) and memory limits (512MB default)
- **FR-008**: System MUST cache tool definitions for session duration to avoid repeated parsing
- **FR-009**: System MUST log all tool invocations (tool name, parameters, duration, result status) for audit trail
- **FR-010**: System MUST return structured error messages to agent when tool execution fails (timeout, permission, parsing errors)

### Key Entities

- **Tool Definition**: Metadata describing a tool (name, description, parameters schema, examples, version, category, security constraints)
- **Tool Registry**: Central repository of available tools (file-based directory structure or database)
- **Tool Session Cache**: In-memory cache of loaded tool definitions for a single agent session
- **Execution Sandbox**: Isolated environment for running tool code (Python subprocess or container)
- **PII Token Map**: Session-specific mapping of PII values to anonymized tokens (e.g., `john@example.com` → `[EMAIL_1]`)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Achieve 95%+ token reduction for queries returning 1000+ records (benchmark: Firestore query returning 5000 cases)
- **SC-002**: Tool discovery completes in <500ms for keyword/category queries
- **SC-003**: Tool execution sandbox successfully terminates runaway processes within timeout window (30s) without crashing main service
- **SC-004**: 100% of PII data (email, phone, ID) is tokenized before entering model context (validated by audit log review)
- **SC-005**: New tools can be added to `tools/` directory and discovered by agents within 1 minute without service restart
- **SC-006**: Agent can successfully execute 100 consecutive tool calls without memory leaks or performance degradation
- **SC-007**: Tool cache reduces repeated definition parsing overhead by >99% (measured by cache hit rate)

## Technical Constraints

- **TC-001**: Tool definitions MUST be stored as Python files with standard docstring format (compatible with Google-style docstrings)
- **TC-002**: Execution sandbox MUST use `multiprocessing` or `docker` for isolation (specific implementation TBD based on deployment environment)
- **TC-003**: PII detection MUST use regex patterns defined in `memory/constitution.md` security guidelines
- **TC-004**: Tool registry MUST support at least 100 tools without performance degradation in discovery (<500ms)
- **TC-005**: Cached tool definitions MUST be invalidated when underlying tool file is modified (file hash comparison)

## Dependencies

- **DEP-001**: Python 3.11+ with `multiprocessing`, `ast`, `inspect` modules for tool parsing and sandboxing
- **DEP-002**: Existing Firestore/GCS client libraries for data access tools
- **DEP-003**: Existing agent framework (Agent 8 conversational system) for tool invocation interface
- **DEP-004**: [NEEDS CLARIFICATION] Docker availability in deployment environment for containerized sandboxing (alternative: `multiprocessing` if Docker unavailable)

## Security & Privacy

- **SEC-001**: Tool code MUST be code-reviewed before deployment to production registry
- **SEC-002**: Sandbox MUST prevent network access unless explicitly whitelisted for specific tools
- **SEC-003**: PII tokenization MUST be irreversible for model - original values stored only in secure session storage with automatic expiration (4 hours)
- **SEC-004**: Tool execution logs MUST NOT contain raw PII - only tokenized versions
- **SEC-005**: Tool registry directory MUST have read-only permissions for service account

## Open Questions

- **Q-001**: Should tool discovery support natural language queries (e.g., "find a way to send Slack messages") or only keyword/category matching?
- **Q-002**: What is the preferred sandbox implementation: Docker containers or Python multiprocessing? (Docker is more secure but requires infrastructure)
- **Q-003**: Should tool definitions include usage examples for agent learning? (Similar to Anthropic's approach)
- **Q-004**: How should tool versioning be handled? Semantic versioning or timestamp-based?

---

**Next Steps**:
1. Clarify open questions (Q-001 to Q-004)
2. Design tool definition schema and directory structure
3. Implement `mcp_adapter.py` module for tool discovery and execution
4. Create example tools for Firestore, GCS, BigQuery
5. Integrate with Agent 8 conversational system
6. Write integration tests for progressive disclosure and context optimization scenarios
