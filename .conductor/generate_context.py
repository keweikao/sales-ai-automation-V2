#!/usr/bin/env python3
"""
Auto-generate PROJECT_CONTEXT.md by scanning the codebase.

Usage:
    python .conductor/generate_context.py

This script scans key directories and files to automatically generate
a project context document that can be shared with any LLM.
"""

import re
import yaml
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_FILE = PROJECT_ROOT / ".conductor" / "PROJECT_CONTEXT.md"

def find_services():
    """Scan for Cloud Run services by looking for cloudbuild files."""
    services = []
    for cb_file in PROJECT_ROOT.glob("**/cloudbuild*.yaml"):
        try:
            with open(cb_file) as f:
                content = yaml.safe_load(f)
                # Extract service name from substitutions or steps
                if content and 'substitutions' in content:
                    svc = content['substitutions'].get('_SERVICE_NAME', '')
                    if svc:
                        services.append({
                            'name': svc,
                            'path': str(cb_file.parent.relative_to(PROJECT_ROOT))
                        })
        except Exception:
            pass
    return services

def find_agents():
    """Scan for Agent definitions in analysis-service."""
    agents = []
    agent_dir = PROJECT_ROOT / "analysis-service" / "src" / "agents"
    if not agent_dir.exists():
        return agents
    
    for py_file in agent_dir.glob("agent*.py"):
        name = py_file.stem
        # Try to find corresponding prompt
        prompt_file = agent_dir / "prompts" / f"{name.replace('_', '-')}.md"
        
        # Extract docstring for description
        desc = ""
        with open(py_file) as f:
            content = f.read()
            match = re.search(r'"""(.+?)"""', content, re.DOTALL)
            if match:
                desc = match.group(1).strip().split('\n')[0][:80]
        
        agents.append({
            'name': name,
            'file': str(py_file.relative_to(PROJECT_ROOT)),
            'prompt': str(prompt_file.relative_to(PROJECT_ROOT)) if prompt_file.exists() else None,
            'description': desc
        })
    
    return sorted(agents, key=lambda x: x['name'])

def find_key_files():
    """Find important files by pattern matching."""
    patterns = {
        'orchestrator': '**/orchestrator.py',
        'main_app': '**/main.py',
        'requirements': '**/requirements.txt',
        'dockerfile': '**/Dockerfile',
    }
    
    files = {}
    for name, pattern in patterns.items():
        found = list(PROJECT_ROOT.glob(pattern))
        files[name] = [str(f.relative_to(PROJECT_ROOT)) for f in found[:5]]
    
    return files

def extract_env_vars():
    """Extract environment variables from example files or cloudbuild."""
    env_vars = set()
    
    # Check cloudbuild files for env vars
    for cb_file in PROJECT_ROOT.glob("**/cloudbuild*.yaml"):
        try:
            with open(cb_file) as f:
                content = f.read()
                # Find common env var patterns
                vars_found = re.findall(r'\$[{_]?([A-Z][A-Z0-9_]+)', content)
                env_vars.update(vars_found)
        except Exception:
            pass

    # Filter to important ones
    important = ['GCP_PROJECT_ID', 'GEMINI_API_KEY', 'SLACK_BOT_TOKEN', 
                 'SLACK_SIGNING_SECRET', 'FIRESTORE_DATABASE']
    return [v for v in important if v in env_vars or True]  # Keep important ones

def count_lines_of_code():
    """Count lines of Python code."""
    total = 0
    for py_file in PROJECT_ROOT.glob("**/*.py"):
        if 'node_modules' in str(py_file) or '.venv' in str(py_file):
            continue
        try:
            with open(py_file) as f:
                total += len(f.readlines())
        except Exception:
            pass
    return total

def generate_context():
    """Generate the PROJECT_CONTEXT.md file."""
    
    agents = find_agents()
    key_files = find_key_files()
    loc = count_lines_of_code()
    
    # Build the markdown content
    content = f"""# Sales AI Automation V2 - Project Context

> 🤖 此文檔由 `.conductor/generate_context.py` 自動生成
> 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M')}

## 專案概述

**Sales AI Automation** 是 iCHEF 銷售團隊的自動化銷售通話分析系統。
業務人員透過 Slack 上傳通話錄音，系統自動轉錄並使用多 Agent 架構分析通話內容，
最後產生客戶摘要報告。

- **程式碼行數**：~{loc:,} 行 Python
- **服務數量**：5 個 Cloud Run 服務

## 技術架構

```
┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Slack App  │───▶│ Transcription    │───▶│ Analysis Service │
│  (上傳入口)  │    │ Service (轉錄)    │    │ (多Agent分析)     │
└─────────────┘    └──────────────────┘    └──────────────────┘
                                                    │
                   ┌──────────────────┐             ▼
                   │  Web Service     │◀───  Firestore (資料庫)
                   │  (客戶摘要頁面)   │
                   └──────────────────┘
```

## 多 Agent 架構

| Agent | 檔案 | Prompt | 說明 |
|-------|------|--------|------|
"""
    
    for agent in agents:
        prompt = f"`{agent['prompt']}`" if agent['prompt'] else "-"
        content += f"| {agent['name']} | `{agent['file']}` | {prompt} | {agent['description'][:50]} |\n"
    
    content += """
## 執行流程 (orchestrator.py)

1. **Phase 1**：Agent 1 + Agent 2 並行執行
2. **Phase 2**：Agent 2 品質檢查迴圈（最多 2 次 refinement）
3. **Phase 3**：競爭對手偵測（條件式）
4. **Phase 4**：Agent 3（綜合前置 Agent 資料）
5. **Phase 5**：Agent 4（產生客戶摘要）

## 資料結構 (Firestore)

```typescript
cases/{caseId} = {
  caseId, customerName, status,
  transcription: { text, segments[] },
  analysis: {
    agents: { agent1, agent2, agent3, agent4 },
    customerSummary: { markdown }
  },
  notification: { slackChannelId, slackThreadTs }
}
```

## 技術棧

| 類別 | 技術 |
|-----|------|
| 語言 | Python 3.10+ |
| 框架 | Flask, Slack Bolt |
| AI | Gemini 2.5 Flash/Pro |
| 資料庫 | Google Firestore |
| 部署 | Google Cloud Run |

## 關鍵檔案

"""
    
    for category, files in key_files.items():
        for f in files[:3]:
            content += f"- `{f}`\n"
    
    content += """
## 編碼規範

- 回應語言：**繁體中文**
- Commit 格式：`feat:`, `fix:`, `docs:`
- Agent Prompt 使用 Markdown 格式

---

*執行 `python .conductor/generate_context.py` 重新生成此文檔*
"""
    
    return content

def main():
    print("🔍 Scanning project structure...")
    content = generate_context()
    
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        f.write(content)
    
    print(f"✅ Generated {OUTPUT_FILE}")
    print("   You can now share this file with any LLM for context.")

if __name__ == "__main__":
    main()
