import json
import subprocess
import sys

MCP_SERVER = "tools/firestore/mcp_server.py"

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
        cwd="."  # Ensure CWD is project root
    )
    
    stdout, stderr = process.communicate(input=json.dumps(request))
    
    if process.returncode != 0:
        raise Exception(f"MCP call failed: {stderr}")
        
    return json.loads(stdout)

def main():
    case_id = "202512-IC002"
    print(f"Checking status for case {case_id}...")
    
    result = call_mcp("firestore_query", {
        "collection": "cases",
        "filters": [],
        "limit": 50,
        "context_mode": "full"
    })
    
    print(f"DEBUG: Raw result: {json.dumps(result, indent=2)}")
    if "results" in result and result["results"]:
        print(f"Found {len(result['results'])} cases.")
        found = False
        for case_data in result["results"]:
            # Check if ID matches (the tool might return ID as 'id' or similar)
            c_id = case_data.get("id")
            if c_id == case_id:
                print(f"✅ Case found: {case_id}")
                print(f"Status: {case_data.get('status')}")
                print(f"Batch ID: {case_data.get('batchId')}")
                print(f"Operation Name: {case_data.get('operationName')}")
                print(f"GCS URI: {case_data.get('gcsUri')}")
                found = True
                break
        
        if not found:
             print(f"❌ Case {case_id} not found in the list of 50 cases.")
             print("Available IDs:", [c.get("id") for c in result["results"]])

if __name__ == "__main__":
    main()
