#!/bin/bash
# MCP 基礎設施快速建置腳本
# 用途：一鍵安裝專案常用的 MCP servers

set -e  # 遇到錯誤立即退出

echo "=========================================="
echo "MCP Infrastructure Setup"
echo "=========================================="
echo ""

# 檢查 Node.js 和 npm 是否已安裝
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm not found. Please install Node.js first."
    echo "   Download from: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js and npm found"
echo ""

# 建立 MCP 配置目錄
echo "📁 Creating MCP configuration directory..."
mkdir -p ~/.claude
echo "✅ Directory created: ~/.claude"
echo ""

# 備份現有配置（如果有）
if [ -f ~/.claude/mcp_config.json ]; then
    backup_file=~/.claude/mcp_config.json.backup.$(date +%Y%m%d_%H%M%S)
    echo "⚠️  Existing mcp_config.json found. Creating backup..."
    cp ~/.claude/mcp_config.json "$backup_file"
    echo "✅ Backup saved: $backup_file"
    echo ""
fi

# 檢查並安裝 MCP servers
echo "=========================================="
echo "Installing MCP Servers"
echo "=========================================="
echo ""

# 1. Google Cloud MCP Server
echo "1️⃣  Installing @modelcontextprotocol/server-gcloud..."
if npm install -g @modelcontextprotocol/server-gcloud 2>/dev/null; then
    echo "✅ gcloud server installed"
else
    echo "⚠️  gcloud server installation failed (may not be available yet)"
    echo "   You can manually create custom tools in /tools/gcloud/"
fi
echo ""

# 2. Filesystem MCP Server（用於檔案操作）
echo "2️⃣  Installing @modelcontextprotocol/server-filesystem..."
if npm install -g @modelcontextprotocol/server-filesystem 2>/dev/null; then
    echo "✅ filesystem server installed"
else
    echo "⚠️  filesystem server installation failed"
fi
echo ""

# 3. Slack MCP Server（如果需要）
echo "3️⃣  Installing @modelcontextprotocol/server-slack..."
if npm install -g @modelcontextprotocol/server-slack 2>/dev/null; then
    echo "✅ slack server installed"
else
    echo "⚠️  slack server installation failed"
fi
echo ""

# 生成 MCP 配置檔案
echo "=========================================="
echo "Generating MCP Configuration"
echo "=========================================="
echo ""

# 取得環境變數
GCP_PROJECT="${GCP_PROJECT:-sales-ai-automation-v2}"
GCP_LOCATION="${GCP_LOCATION:-asia-east1}"
GOOGLE_CREDS="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/application_default_credentials.json}"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cat > ~/.claude/mcp_config.json <<EOF
{
  "mcpServers": {
    "gcloud": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-gcloud"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "$GOOGLE_CREDS",
        "GCP_PROJECT": "$GCP_PROJECT",
        "GCP_LOCATION": "$GCP_LOCATION"
      },
      "disabled": false
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "$PROJECT_ROOT"],
      "disabled": false
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "\${SLACK_BOT_TOKEN}"
      },
      "disabled": true
    },
    "custom_firestore": {
      "command": "python3",
      "args": ["$PROJECT_ROOT/tools/firestore/mcp_server.py"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "$GOOGLE_CREDS",
        "GCP_PROJECT": "$GCP_PROJECT"
      },
      "disabled": false
    },
    "gcp_ai": {
      "command": "python3",
      "args": ["$PROJECT_ROOT/tools/gcp_ai/mcp_server.py"],
      "env": {
        "GEMINI_API_KEY": "\${GEMINI_API_KEY}"
      },
      "disabled": false
    },
    "cloud_tasks": {
      "command": "python3",
      "args": ["$PROJECT_ROOT/tools/cloud_tasks/mcp_server.py"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "$GOOGLE_CREDS",
        "GCP_PROJECT": "$GCP_PROJECT"
      },
      "disabled": false
    }
  }
}
EOF

echo "✅ Configuration file created: ~/.claude/mcp_config.json"
echo ""

# 顯示配置內容
echo "=========================================="
echo "Configuration Summary"
echo "=========================================="
cat ~/.claude/mcp_config.json
echo ""

# 測試配置
echo "=========================================="
echo "Testing MCP Configuration"
echo "=========================================="
echo ""

echo "📝 To test MCP servers, restart Claude Code and check for mcp__ prefixed tools."
echo ""

# 建立自定義 tools（如果尚未存在）
echo "=========================================="
echo "Setting up Custom Tools"
echo "=========================================="
echo ""

if [ ! -d "$PROJECT_ROOT/tools/firestore" ]; then
    echo "📁 Creating custom Firestore tools..."
    mkdir -p "$PROJECT_ROOT/tools/firestore"

    cat > "$PROJECT_ROOT/tools/firestore/mcp_server.py" <<'PYEOF'
#!/usr/bin/env python3
"""
Custom MCP Server for Firestore Operations

Provides optimized Firestore query tools with automatic filtering
and field selection to reduce token usage.
"""
import sys
import json
import os
from typing import Any, Dict, List, Optional

try:
    from google.cloud import firestore
except ImportError:
    firestore = None

def query_firestore(
    collection: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    limit: int = 10,
    fields: Optional[List[str]] = None,
    order_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Query Firestore with filtering and field selection.

    Args:
        collection: Collection name
        filters: List of filter conditions [{"field": "status", "op": "==", "value": "active"}]
        limit: Maximum number of results
        fields: Fields to return (reduces token usage)
        order_by: Field to order by

    Returns:
        Filtered and summarized results
    """
    if firestore is None:
        return {"error": "google-cloud-firestore not installed"}

    try:
        db = firestore.Client()
        query = db.collection(collection)

        # Apply filters
        if filters:
            for f in filters:
                query = query.where(f["field"], f["op"], f["value"])

        # Apply ordering
        if order_by:
            query = query.order_by(order_by)

        # Apply limit
        query = query.limit(limit)

        # Execute query
        docs = list(query.stream())

        # Extract data
        results = []
        for doc in docs:
            data = doc.to_dict()

            # Filter fields if specified
            if fields:
                data = {k: data.get(k) for k in fields if k in data}

            results.append({
                "id": doc.id,
                **data
            })

        return {
            "count": len(results),
            "data": results,
            "collection": collection
        }

    except Exception as e:
        return {"error": str(e)}

# MCP Protocol Handler
def handle_request(request: dict) -> dict:
    method = request.get("method")

    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "firestore_query",
                    "description": "Query Firestore with filtering and field selection to reduce token usage",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "collection": {"type": "string", "description": "Collection name"},
                            "filters": {
                                "type": "array",
                                "description": "Filter conditions",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "field": {"type": "string"},
                                        "op": {"type": "string", "enum": ["==", "!=", "<", "<=", ">", ">=", "in", "array-contains"]},
                                        "value": {"description": "Filter value"}
                                    }
                                }
                            },
                            "limit": {"type": "integer", "default": 10},
                            "fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Fields to return (omit for all fields)"
                            },
                            "order_by": {"type": "string", "description": "Field to order by"}
                        },
                        "required": ["collection"]
                    }
                }
            ]
        }

    elif method == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"]["arguments"]

        if tool_name == "firestore_query":
            return query_firestore(**arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    else:
        return {"error": f"Unknown method: {method}"}

if __name__ == "__main__":
    # MCP server main loop
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
        except Exception as e:
            error_response = {"error": str(e)}
            print(json.dumps(error_response))
            sys.stdout.flush()
PYEOF

    chmod +x "$PROJECT_ROOT/tools/firestore/mcp_server.py"
    echo "✅ Custom Firestore MCP server created"
else
    echo "✅ Custom tools already exist"
fi
echo ""

# 完成
echo "=========================================="
echo "✅ MCP Infrastructure Setup Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Restart Claude Code to load the new MCP configuration"
echo "2. Check for mcp__ prefixed tools in the tools list"
echo "3. Review QUICK_START_FOR_AI.md → 開發前置檢查清單 section for usage guidelines"
echo ""
echo "Configuration file: ~/.claude/mcp_config.json"
echo "Custom tools: $PROJECT_ROOT/tools/"
echo ""
echo "🎉 Happy coding with optimized token usage!"
