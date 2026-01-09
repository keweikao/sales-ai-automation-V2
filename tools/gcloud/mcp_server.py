"""MCP Server for General Google Cloud Operations
Category: gcloud
Version: 1.0.0
Description: Manage IAM, Cloud Build, and Cloud Run resources efficiently.
"""
import sys
import json
import subprocess
from typing import Dict, Any, List

# MCP Tool Definitions
TOOLS = [
    {
        "name": "gcloud_iam_policy_binding",
        "description": "Add or remove IAM policy binding for a project or resource.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "GCP Project ID"},
                "member": {"type": "string", "description": "Member to bind (e.g., serviceAccount:email)"},
                "role": {"type": "string", "description": "Role to assign (e.g., roles/storage.admin)"},
                "action": {"type": "string", "enum": ["add", "remove"], "default": "add"}
            },
            "required": ["project", "member", "role"]
        }
    },
    {
        "name": "gcloud_builds_submit",
        "description": "Submit a Cloud Build job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "config": {"type": "string", "description": "Path to cloudbuild.yaml"},
                "source": {"type": "string", "default": ".", "description": "Source directory"},
                "substitutions": {"type": "object", "description": "Key-value pairs for substitutions"},
                "async_mode": {"type": "boolean", "default": False, "description": "Return immediately with build ID"}
            },
            "required": ["config"]
        }
    },
    {
        "name": "gcloud_run_deploy",
        "description": "Deploy a Cloud Run service.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Service name"},
                "image": {"type": "string", "description": "Container image URI"},
                "region": {"type": "string", "default": "asia-east1"},
                "platform": {"type": "string", "default": "managed"},
                "allow_unauthenticated": {"type": "boolean", "default": True},
                "env_vars": {"type": "object", "description": "Environment variables"},
                "secrets": {"type": "object", "description": "Secrets mapping"}
            },
            "required": ["service", "image"]
        }
    },
    {
        "name": "gcloud_get_iam_policy",
        "description": "Get IAM policy for a project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "GCP Project ID"}
            },
            "required": ["project"]
        }
    },
    {
        "name": "gcloud_builds_list",
        "description": "List Cloud Build jobs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
                "ongoing": {"type": "boolean", "default": False}
            }
        }
    }
]

def run_command(cmd: List[str]) -> Dict[str, Any]:
    """Execute shell command and return structured result."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return {
            "status": "success",
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "error": e.stderr.strip(),
            "stdout": e.stdout.strip(),
            "return_code": e.returncode
        }

def handle_builds_list(params: Dict[str, Any]) -> Dict[str, Any]:
    cmd = ["gcloud", "builds", "list", "--format=json"]
    
    if params.get("limit"):
        cmd.append(f"--limit={params['limit']}")
        
    if params.get("ongoing"):
        cmd.append("--ongoing")
        
    result = run_command(cmd)
    if result["status"] == "success":
        try:
            result["builds"] = json.loads(result["stdout"])
        except json.JSONDecodeError:
            result["status"] = "error"
            result["error"] = "Failed to parse builds JSON"
    return result

def handle_get_iam_policy(params: Dict[str, Any]) -> Dict[str, Any]:
    cmd = [
        "gcloud", "projects", "get-iam-policy",
        params["project"],
        "--format=json"
    ]
    result = run_command(cmd)
    if result["status"] == "success":
        try:
            result["policy"] = json.loads(result["stdout"])
        except json.JSONDecodeError:
            result["status"] = "error"
            result["error"] = "Failed to parse IAM policy JSON"
    return result

def handle_iam_binding(params: Dict[str, Any]) -> Dict[str, Any]:
    cmd = [
        "gcloud", "projects", 
        "add-iam-policy-binding" if params.get("action", "add") == "add" else "remove-iam-policy-binding",
        params["project"],
        f"--member={params['member']}",
        f"--role={params['role']}",
        "--format=json"
    ]
    return run_command(cmd)

def handle_builds_submit(params: Dict[str, Any]) -> Dict[str, Any]:
    cmd = [
        "gcloud", "builds", "submit",
        params.get("source", "."),
        f"--config={params['config']}",
        "--format=json"
    ]
    
    if params.get("substitutions"):
        subs = ",".join([f"{k}={v}" for k, v in params["substitutions"].items()])
        cmd.append(f"--substitutions={subs}")
        
    if params.get("async_mode"):
        cmd.append("--async")
        
    return run_command(cmd)

def handle_run_deploy(params: Dict[str, Any]) -> Dict[str, Any]:
    cmd = [
        "gcloud", "run", "deploy", params["service"],
        f"--image={params['image']}",
        f"--region={params.get('region', 'asia-east1')}",
        f"--platform={params.get('platform', 'managed')}",
        "--format=json"
    ]
    
    if params.get("allow_unauthenticated"):
        cmd.append("--allow-unauthenticated")
        
    if params.get("env_vars"):
        env = ",".join([f"{k}={v}" for k, v in params["env_vars"].items()])
        cmd.append(f"--set-env-vars={env}")
        
    if params.get("secrets"):
        secrets = ",".join([f"{k}={v}" for k, v in params["secrets"].items()])
        cmd.append(f"--set-secrets={secrets}")
        
    return run_command(cmd)

def handle_request(request: dict) -> dict:
    method = request.get("method")
    
    if method == "tools/list":
        return {"tools": TOOLS}
    elif method == "tools/call":
        tool_name = request["params"]["name"]
        args = request["params"]["arguments"]
        
        if tool_name == "gcloud_get_iam_policy":
            return handle_get_iam_policy(args)
        elif tool_name == "gcloud_builds_list":
            return handle_builds_list(args)
        elif tool_name == "gcloud_iam_policy_binding":
            return handle_iam_binding(args)
        elif tool_name == "gcloud_builds_submit":
            return handle_builds_submit(args)
        elif tool_name == "gcloud_run_deploy":
            return handle_run_deploy(args)
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
