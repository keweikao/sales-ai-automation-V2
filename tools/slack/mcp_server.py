"""
MCP Server for Slack Send Message Tool

Provides a tool to send messages to Slack channels.
"""
import sys
import json
from typing import Any
from .send_message import send_message

# MCP Tool Definition for slack_send_message
TOOL_DEFINITION = {
    "name": "slack_send_message",
    "description": "Sends a message to a Slack channel.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "channel": {"type": "string", "description": "The Slack channel to send the message to."},
            "text": {"type": "string", "description": "The text of the message."}
        },
        "required": ["channel", "text"]
    }
}

def handle_request(request: dict) -> dict:
    method = request.get("method")

    if method == "tools/list":
        return {"tools": [TOOL_DEFINITION]}
    elif method == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"]["arguments"]

        if tool_name == "slack_send_message":
            return send_message(**arguments)
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
