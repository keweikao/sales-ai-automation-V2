# Scripts Overview

整理腳本入口與分類，避免重複與混用。

## 目錄結構

- `bash/`, `powershell/` — 常用自動化腳本的 Bash/PowerShell 版本。
- `deploy_all.sh` — 觸發整體部署的封裝腳本。
- `setup_mcp_infrastructure.sh` — 建立 MCP 相關基礎設施。
- `export_project_skeleton.py` — 匯出專案骨架。

## 根目錄單檔腳本（保留原路徑）

以下腳本目前在專案根目錄使用，已在多處文件引用，路徑暫不調整：

| Script | Purpose |
| --- | --- |
| `quick_hf_check.py`, `verify_huggingface_token.py` | Hugging Face Token 快速檢查/驗證 |
| `cleanup_firestore.py`, `clear_firestore.sh` | Firestore 清理工具 |
| `check_case.py`, `detailed_case_query.py`, `query_case_summary.py`, `query_logs.py` | Case/Log 查詢輔助 |
| `quick_check_latest.py` | 快速狀態檢查 |
| `setup_mcp_infrastructure.sh` | MCP 基礎設施設定（保留位置以相容現有指引） |

## 遷移建議

- 新增腳本：優先放入 `scripts/bash` 或 `scripts/powershell`，並在此檔補充用途。
- 既有根目錄腳本：若要遷移，先更新文件/指南中的執行路徑，再移動檔案；必要時保留短期 symlink 避免 CI/文件斷鏈。

> 建議：新增腳本時優先放入 `scripts/`（依作業系統/用途分子資料夾），並在此 README 增補說明；若需遷移既有根目錄腳本，請先更新引用文件後再移動。
