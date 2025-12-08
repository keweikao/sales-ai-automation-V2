import json
import subprocess
import sys

MCP_SERVER = "tools/gcloud/mcp_server.py"
SOURCE_USER = "user:stephen.kao@ichef.com.tw"
TARGET_USER = "user:keweikao@gmail.com"
PROJECT_ID = "sales-ai-automation-v2"

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
    print(f"Fetching IAM policy for {PROJECT_ID}...")
    response = call_mcp("gcloud_get_iam_policy", {"project": PROJECT_ID})
    
    if response.get("status") != "success":
        print(f"Error fetching policy: {response}")
        return

    policy = response.get("policy", {})
    bindings = policy.get("bindings", [])
    
    roles_to_add = []
    
    # Explicitly assign Editor and IAM Admin roles instead of copying Owner
    # to avoid ORG_MUST_INVITE_EXTERNAL_OWNERS error
    target_roles = [
        "roles/editor",
        "roles/resourcemanager.projectIamAdmin",
        "roles/cloudbuild.builds.editor",
        "roles/run.admin",
        "roles/storage.admin",
        "roles/datastore.owner",
        "roles/iam.serviceAccountUser"
    ]
    
    roles_to_add = []
    
    # Check which roles the target user is missing
    # We need to fetch the policy again or just try to add them (idempotent-ish)
    # But let's check current bindings to avoid redundant calls
    
    current_roles = set()
    for binding in bindings:
        members = binding.get("members", [])
        role = binding.get("role")
        if TARGET_USER in members:
            current_roles.add(role)
            
    for role in target_roles:
        if role not in current_roles:
            roles_to_add.append(role)
            print(f"Will add role: {role}")
        else:
            print(f"Target user already has: {role}")

    if not roles_to_add:
        print("No new roles to migrate.")
        return

    print(f"\nMigrating {len(roles_to_add)} roles...")
    
    for role in roles_to_add:
        print(f"Adding role {role} to {TARGET_USER}...")
        result = call_mcp("gcloud_iam_policy_binding", {
            "project": PROJECT_ID,
            "member": TARGET_USER,
            "role": role,
            "action": "add"
        })
        
        if result.get("status") == "success":
            print("✅ Success")
        else:
            print(f"❌ Failed: {result.get('error')}")

if __name__ == "__main__":
    main()
