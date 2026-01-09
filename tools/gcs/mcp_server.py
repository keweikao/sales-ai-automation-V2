"""
MCP Server for Google Cloud Storage Upload Tool

Provides a tool to upload files to Google Cloud Storage.
"""
import sys
import json
from .upload import upload

# MCP Tool Definitions
TOOLS = [
    {
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
    },
    {
        "name": "gcs_list",
        "description": "Lists blobs in the specified GCS bucket.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bucket_name": {"type": "string", "description": "The name of the GCS bucket."},
                "prefix": {"type": "string", "description": "Prefix to filter blobs."}
            },
            "required": ["bucket_name"]
        }
    }
]

def list_blobs(bucket_name: str, prefix: str = None) -> dict:
    from google.cloud import storage
    storage_client = storage.Client()
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix)
    
    results = []
    for blob in blobs:
        results.append({
            "name": blob.name,
            "size": blob.size,
            "updated": blob.updated.isoformat() if blob.updated else None
        })
    return {"blobs": results}

def handle_request(request: dict) -> dict:
    method = request.get("method")

    if method == "tools/list":
        return {"tools": TOOLS}
    elif method == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"]["arguments"]

        if tool_name == "gcs_upload":
            return upload(**arguments)
        elif tool_name == "gcs_list":
            return list_blobs(**arguments)
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
