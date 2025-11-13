"""
MCP Server for Google Cloud Storage Upload Tool

Provides a tool to upload files to Google Cloud Storage.
"""
import sys
import json
from typing import Any
from .upload import upload

# MCP Tool Definition for gcs_upload
TOOL_DEFINITION = {
    "name": "gcs_upload",
    "description": "Uploads a file to the specified GCS bucket.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "bucket_name": {"type": "string", "description": "The name of the GCS bucket."},
            "source_file_name": {"type": "string", "description": "The path to the file to upload."},
            "destination_blob_name": {"type": "string", "description": "The name of the blob in the bucket."}
        },
        "required": ["bucket_name", "source_file_name", "destination_blob_name"]
    }
}

def handle_request(request: dict) -> dict:
    method = request.get("method")

    if method == "tools/list":
        return {"tools": [TOOL_DEFINITION]}
    elif method == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"]["arguments"]

        if tool_name == "gcs_upload":
            return upload(**arguments)
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
