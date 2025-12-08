import os
import sys
import json
import yaml
import fnmatch

def check_json(file_path):
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        return True
    except Exception as e:
        print(f"❌ JSON Error in {file_path}: {e}")
        return False

def check_yaml(file_path):
    try:
        with open(file_path, 'r') as f:
            yaml.safe_load(f)
        return True
    except Exception as e:
        print(f"❌ YAML Error in {file_path}: {e}")
        return False

def should_ignore(path, ignore_patterns):
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(path, pattern) or pattern in path.split(os.sep):
            return True
    return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_syntax.py [json|yaml]")
        sys.exit(1)

    mode = sys.argv[1]
    root_dir = "."
    ignore_patterns = [
        "node_modules", 
        ".git", 
        ".venv", 
        "venv", 
        "__pycache__", 
        ".pytest_cache",
        ".specify",
        "dist",
        "build",
        ".devcontainer",
        ".vscode"
    ]
    
    has_error = False
    
    for root, dirs, files in os.walk(root_dir):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_patterns)]
        
        for file in files:
            file_path = os.path.join(root, file)
            if should_ignore(file_path, ignore_patterns):
                continue
                
            if mode == "json" and file.endswith(".json"):
                if not check_json(file_path):
                    has_error = True
            elif mode == "yaml" and (file.endswith(".yaml") or file.endswith(".yml")):
                if not check_yaml(file_path):
                    has_error = True

    if has_error:
        sys.exit(1)
    else:
        print(f"✅ All {mode.upper()} files passed syntax check.")

if __name__ == "__main__":
    main()
