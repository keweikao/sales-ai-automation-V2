import json
import subprocess
import sys

MCP_SERVER = "tools/gcloud/mcp_server.py"

def call_mcp(tool_name, args):
    request = {
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": args
        }
    }
    
    process = subprocess.Popen(
        [sys.executable, MCP_SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=json.dumps(request))
    
    if process.returncode != 0:
        raise Exception(f"MCP call failed: {stderr}")
        
    return json.loads(stdout)

def main():
    print("Checking ongoing builds...")
    result = call_mcp("gcloud_builds_list", {
        "limit": 5,
        "ongoing": True
    })
    
    if result.get("status") == "success":
        builds = result.get("builds", [])
        if not builds:
            print("No ongoing builds found.")
            # Check recent builds to see if it finished
            print("Checking recent builds...")
            result = call_mcp("gcloud_builds_list", {
                "limit": 5,
                "ongoing": False
            })
            builds = result.get("builds", [])
            
        for build in builds:
            print(f"Build ID: {build.get('id')}")
            print(f"Status: {build.get('status')}")
            print(f"Create Time: {build.get('createTime')}")
            print("-" * 20)
    else:
        print(f"❌ Failed to list builds: {result.get('error')}")

if __name__ == "__main__":
    main()
