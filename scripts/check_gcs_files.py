import json
import subprocess
import sys

def call_mcp(tool_name, args):
    request = {
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": args
        }
    }
    
    process = subprocess.Popen(
        [sys.executable, "-m", "tools.gcs.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="."
    )
    
    stdout, stderr = process.communicate(input=json.dumps(request))
    
    if process.returncode != 0:
        raise Exception(f"MCP call failed: {stderr}")
        
    return json.loads(stdout)

def main():
    bucket_name = "sales-ai-audio-bucket"
    print(f"Checking files in {bucket_name}...")
    
    result = call_mcp("gcs_list", {
        "bucket_name": bucket_name,
        "prefix": "slack/202512-IC002/"
    })
    
    if "blobs" in result:
        blobs = result["blobs"]
        # Sort by updated time descending
        blobs.sort(key=lambda x: x.get("updated", ""), reverse=True)
        
        print(f"Found {len(blobs)} files. Top 10 most recent:")
        for blob in blobs[:10]:
            print(f"Name: {blob.get('name')}")
            print(f"Size: {blob.get('size')}")
            print(f"Updated: {blob.get('updated')}")
            print("-" * 20)
    else:
        print(f"❌ Failed to list blobs: {result.get('error')}")

if __name__ == "__main__":
    main()
