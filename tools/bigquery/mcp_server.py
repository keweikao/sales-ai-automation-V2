"""
MCP Server for Google BigQuery Query Tool

Provides a tool to run BigQuery queries.
"""
import sys
import json
from typing import Any
from .query import query

# MCP Tool Definition for bigquery_query
TOOL_DEFINITION = {
    "name": "bigquery_query",
    "description": "Runs a BigQuery query and returns the results.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query_string": {"type": "string", "description": "The BigQuery query to execute."}
        },
        "required": ["query_string"]
    }
}

def handle_request(request: dict) -> dict:
    method = request.get("method")

    if method == "tools/list":
        return {"tools": [TOOL_DEFINITION]}
    elif method == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"]["arguments"]

        if tool_name == "bigquery_query":
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
