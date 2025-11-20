# 專案骨架匯出指南

此指南說明如何使用 `scripts/export_project_skeleton.py` 將目前專案的核心框架、SOP 文件與模板打包到全新的目錄，以便快速建立下一個以 Spec Kit 為基礎的專案。

---

## 1. 需求條件

- Python 3.10+（與現有開發環境一致）
- 已安裝專案依賴（可透過 `poetry install`，僅用於執行腳本）
- 目標資料夾**不存在或為空**，避免覆蓋既有檔案

---

## 2. 操作步驟

1. 選擇要產生骨架的目錄。例如：`~/workspace/new-spec-kit`
2. 在專案根目錄執行下列任一指令：

```bash
python scripts/export_project_skeleton.py ~/workspace/new-spec-kit
# 或
poetry run python scripts/export_project_skeleton.py ~/workspace/new-spec-kit
```

3. 若目的地已存在且為空，亦可加入 `--overwrite` 參數：

```bash
python scripts/export_project_skeleton.py ~/workspace/new-spec-kit --overwrite
```

---

## 3. 匯出內容

- **核心自動化與設定**：`Makefile`、`pyproject.toml`、`Dockerfile*`、所有 `cloudbuild*.yaml`、`.gitignore`、`.dockerignore`、`.markdownlint-cli2.jsonc`
- **SOP 與指引**：`QUICK_START_FOR_AI.md`、`DEVELOPMENT_GUIDELINES.md`、`TOKEN_OPTIMIZATION_GUIDE.md`、`memory/constitution.md`
- **通用文件**：`docs/ai-collaboration-playbook.md`、`docs/credential-management.md`、`docs/subagent_alternatives.md`、`docs/local-development.md`、`docs/installation.md`
- **必備目錄**：`.specify/`、`.devcontainer/`、`templates/`、`tools/`、`scripts/`（包含 MCP/自動化腳本）
- **服務骨架**：
  - `analysis-service/`：保留 `Dockerfile`、`cloudbuild.yaml`、`requirements.txt`，並建立空的 `src/`、`tests/`
  - `web-service/`：保留 `Dockerfile`、`README.md`、`requirements.txt`，並建立空的 `src/`、`static/`、`templates/`、`tests/`
- **測試骨架**：複製 `tests/conftest.py`，並建立空的 `tests/unit/`

所有由腳本建立的空資料夾都會附帶 `.gitkeep` 以確保版本控制。

---

## 4. 匯出後必做事項

1. **更新專案資訊**
   - 調整 `pyproject.toml`（專案名稱、版本、作者、描述）
   - 修改 Docker 映像名稱與 Cloud Build 觸發設定
2. **重新設定文件**
   - 更新 `README.md`、`PROJECT_README.md` 或任何對外文件，改成新專案說明
3. **初始化 MCP/Secrets**
   - 視需求重新執行 `scripts/setup_mcp_infrastructure.sh`
   - 寫入新的環境變數與祕密管理機制
4. **填入服務/測試內容**
   - 在 `analysis-service/src`、`web-service/src` 實作新的商業邏輯
   - 在 `tests/unit` 新增與新專案對應的測試
5. **檢查 CI/CD**
   - 驗證 `cloudbuild*.yaml` 是否需要調整 GCP 專案、主機名稱或 artifact registry

---

## 5. 疑難排解

- **部分檔案缺失**：腳本會列出未被複製的路徑，請確認是否在原始專案被刪除或更名。
- **目標資料夾已有內容**：請清空或以 `--overwrite` 參數覆寫空資料夾。
- **權限問題**：確保對目標路徑具有寫入權限，必要時以 `mkdir -p <path>` 先建立資料夾。

完成以上步驟後，新專案即可沿用完整的 Spec Kit 工作流與最佳實務，僅需聚焦在新的業務邏輯與服務開發。祝開發順利！🚀
