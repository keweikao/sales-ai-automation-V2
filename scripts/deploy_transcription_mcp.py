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
    print("Submitting build for transcription-service...")
    result = call_mcp("gcloud_builds_submit", {
        "config": "deploy/transcription/cloudbuild.transcription.yaml",
        "source": ".",
        "async_mode": False
    })
    
    if result.get("status") == "success":
        print("✅ Build submitted successfully")
        print(result.get("stdout"))
    else:
        print(f"❌ Build failed: {result.get('error')}")
        print(result.get("stderr"))

if __name__ == "__main__":
    main()
