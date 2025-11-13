# Subagent Alternatives for Non-Claude Models

This document outlines strategies for achieving functionalities typically provided by Claude's Subagent system when using other AI models like Gemini or Codex. The focus is on leveraging Model Context Protocol (MCP) tools and direct tool calls while considering token cost optimization.

## 1. Understanding Subagent Functionality

Claude's Subagents offer specialized capabilities, primarily for:

* **Code Exploration**: Searching large codebases, understanding architecture, identifying relevant files.
* **Multi-round Trial-and-Error**: Iterative testing, debugging, and refining solutions in an isolated context without polluting the main conversation.

## 2. Alternatives using MCP Tools and Direct Tool Calls

For non-Claude models, these functionalities can be achieved by strategically combining MCP tools and direct tool calls.

### 2.1 Code Exploration Alternatives

| Subagent Functionality | MCP/Direct Tool Alternative | Token Optimization Considerations |
|------------------------|-----------------------------|-----------------------------------|
| **Search Codebase**    | `mcp__filesystem.grep` (if available) or `Bash("grep ...")` | Use precise regex patterns. Limit search depth/scope. |
|                        | `mcp__filesystem.glob` (if available) or `Bash("find ...")` | Filter by file types. Avoid large directories. |
|                        | `read_many_files` (if available) | Specify exact files/patterns. Use `limit` and `offset` for large files. |
| **Understand Architecture** | `read_file` for `plan.md`, `spec.md`, `DEVELOPMENT_LOG.md` | Focus on high-level overview documents first. |
|                        | `codebase_investigator` (if available) | Use for complex, system-wide analysis. |
| **Identify Relevant Files** | `list_directory` for specific directories. | Use `ignore` patterns to exclude irrelevant files. |

**Example Scenario: Find all Python files implementing an "Agent" class.**

* **Subagent (Claude)**: `Task(subagent_type="Explore", prompt="Find all Agent classes in Python files.")`
* **Gemini/Codex Alternative**:
    1. `list_directory(dir_path="analysis-service/src/agents")` to get agent files.
    2. `Bash("grep -r 'class .*Agent' analysis-service/src/agents/")` to find class definitions.
    3. `read_file` for specific files to understand implementation.

### 2.2 Multi-round Trial-and-Error Alternatives

| Subagent Functionality | MCP/Direct Tool Alternative | Token Optimization Considerations |
|------------------------|-----------------------------|-----------------------------------|
| **Iterative Testing/Debugging** | `Bash("python -m pytest ...")` or `Bash("python my_script.py")` | Run tests/scripts in isolated shell commands. |
|                        | `read_file` for logs/output. | Only read relevant parts of output. |
|                        | `write_file` for temporary code changes. | Keep changes minimal and focused. |
| **Parameter/Model Tuning** | `Bash` commands to run scripts with different parameters. | Capture only essential results, not full logs. |
|                        | `mcp__gcp_ai.generate_content` with different models/prompts. | Compare outputs directly. |

**Example Scenario: Test different Gemini models for a specific prompt.**

* **Subagent (Claude)**: `Task(subagent_type="general-purpose", prompt="Test gemini-pro and gemini-1.5-flash with prompt X.")`
* **Gemini/Codex Alternative**:
    1. `mcp__gcp_ai.generate_content(model="gemini-pro", prompt="...")`
    2. Analyze output.
    3. `mcp__gcp_ai.generate_content(model="gemini-1.5-flash", prompt="...")`
    4. Analyze output.
    5. Compare results in the main conversation.

## 3. Token Cost Considerations

When using alternatives, be mindful of token usage:

* **Minimize output**: Request only necessary information from tool calls.
* **Filter aggressively**: Use `grep`, `find`, `jq` (if available) to filter data before reading it into the main context.
* **Batch operations**: Combine multiple small operations into a single tool call where possible.
* **Leverage MCP's context optimization**: Utilize `context_mode` in tools like `firestore_query` to reduce data returned to the model.

## 4. Best Practices for Non-Claude Models

* **Clear Planning**: Before executing complex tasks, formulate a clear plan to minimize unnecessary tool calls.
* **Iterative Refinement**: Break down large tasks into smaller, manageable steps.
* **Explicit State Management**: Since there's no isolated subagent context, explicitly manage intermediate results and state in temporary files or variables.
* **Utilize `DEVELOPMENT_LOG.md`**: Document trial-and-error processes and key findings to maintain context.

By following these guidelines, non-Claude models can effectively perform complex development tasks, leveraging the project's MCP infrastructure and direct tool access.
