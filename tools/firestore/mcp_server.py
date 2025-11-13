"MCP Server for Google Firestore Query Tool

Provides a tool to query Firestore collections with context optimization."
import sys
import json
from typing import Any
from .query import query

# MCP Tool Definition for firestore_query
TOOL_DEFINITION = {
    "name": "firestore_query",
    "description": "Query Firestore collection with automatic context optimization.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "collection": {"type": "string", "description": "Collection name (e.g., 'cases', 'customers')"},
            "filters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "op": {"type": "string", "enum": ["==", "!=", "<", "<=", ">", ">=", "in", "array-contains"]},
                        "value": {"type": "string"} # Simplified for now, can be Any
                    },
                    "required": ["field", "op", "value"]
                },
                "description": "List of filter dicts with structure: [{"field": str, "op": str, "value": Any}]"
            },
            "order_by": {"type": "string", "description": "Field name for sorting (optional)"},
            "limit": {"type": "integer", "default": 100, "description": "Maximum number of results to return"},
            "context_mode": {"type": "string", "enum": ["minimal", "full", "aggregate"], "default": "minimal", "description": "Context optimization mode"}
        },
        "required": ["collection", "filters"]
    }
}

def handle_request(request: dict) -> dict:
    method = request.get("method")

    if method == "tools/list":
        return {"tools": [TOOL_DEFINITION]}
    elif method == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"]["arguments"]

        if tool_name == "firestore_query":
            return query(**arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    else:
        return {"error": f"Unknown method: {method}"}

if __name__ == "__main__":
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response, ensure_ascii=False))
            sys.stdout.flush()
        except Exception as e:
            error_response = {"error": str(e)}
            print(json.dumps(error_response, ensure_ascii=False))
            sys.stdout.flush()
