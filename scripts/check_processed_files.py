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
        [sys.executable, "-m", "tools.firestore.mcp_server"],
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
    print("Checking recent processed_files...")
    
    # Query processed_files collection
    # We'll try to sort by created_at or upload_time if possible, 
    # but for now let's just get the latest 10 and inspect them.
    result = call_mcp("firestore_query", {
        "collection": "processed_files",
        "filters": [], # No filters, just list
        "limit": 10,
        "context_mode": "full"
    })
    
    if "results" in result and result["results"]:
        files = result["results"]
        print(f"Found {len(files)} files:")
        for f in files:
            print(f"ID: {f.get('id')}")
            print(f"Filename: {f.get('filename')}")
            print(f"Status: {f.get('status')}")
            print(f"Created At: {f.get('created_at')}")
            print(f"GCS URI: {f.get('gcs_uri')}")
            print("-" * 20)
    else:
        print("No files found in processed_files.")

if __name__ == "__main__":
    main()
