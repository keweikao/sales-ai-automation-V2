# GitHub Actions 自動部署設置指南

本文檔說明如何設置 GitHub Actions 自動部署到 GCP Cloud Run。

## 概述

我們已經建立了完整的 CI/CD 流程：

- **CI Workflow** (`.github/workflows/ci.yml`): 在每次 push 和 PR 時執行程式碼品質檢查
- **Deploy Workflow** (`.github/workflows/deploy.yml`): 在 push 到 main 分支時自動部署到 GCP

## 部署流程

當程式碼推送到 `main` 分支時，GitHub Actions 會自動執行以下步驟：

1. **品質檢查階段**:
   - Markdown linting (markdownlint-cli2)
   - Python 語法檢查
   - YAML 語法檢查
   - JSON 語法檢查
   - 完整測試套件 (`make test-all`)

2. **部署階段**（只在品質檢查通過後執行）:
   - 認證到 GCP
   - 配置 Docker 與 Artifact Registry
   - 執行部署腳本 (`scripts/deploy_all.sh`)
   - 顯示部署結果

## 設置 GitHub Secrets

### 步驟 1: 獲取 GCP 服務帳戶金鑰

您已經有服務帳戶金鑰。如需重新生成，請執行：

```bash
gcloud iam service-accounts keys create gcp-key.json \
  --iam-account=497329205771-compute@developer.gserviceaccount.com
```

### 步驟 2: 在 GitHub 設置 Secret

1. 前往 GitHub 儲存庫頁面
2. 點擊 **Settings** → **Secrets and variables** → **Actions**
3. 點擊 **New repository secret**
4. 設置以下 Secret:

   **Secret 名稱**: `GCP_SERVICE_ACCOUNT_KEY`

   **Secret 值**: 將整個 JSON 金鑰檔案的內容貼上（包含大括號）

   例如:

   ```json
   {
     "type": "service_account",
     "project_id": "sales-ai-automation-v2",
     "private_key_id": "...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     "client_email": "497329205771-compute@developer.gserviceaccount.com",
     ...
   }
   ```

5. 點擊 **Add secret**

### 步驟 3: 驗證設置

1. 推送任何變更到 `main` 分支
2. 前往 GitHub 儲存庫的 **Actions** 標籤
3. 查看 "Deploy to GCP" workflow 的執行狀態

## 手動觸發部署

除了自動部署外，您也可以手動觸發部署：

1. 前往 **Actions** 標籤
2. 選擇 "Deploy to GCP" workflow
3. 點擊 **Run workflow**
4. 選擇分支（通常是 main）
5. 點擊 **Run workflow** 按鈕

## 本地部署 vs GitHub Actions 部署

### 本地部署（使用 `/deploy` 命令）

- 適合開發和測試
- 執行本地品質檢查
- 需要本地 gcloud 認證
- 提供即時反饋

### GitHub Actions 部署

- 適合正式發佈
- 在乾淨的環境中執行
- 自動化且可追蹤
- 所有團隊成員都能看到部署歷史

## 疑難排解

### 部署失敗：認證錯誤

確認 `GCP_SERVICE_ACCOUNT_KEY` Secret 已正確設置，且 JSON 格式完整。

### 部署失敗：權限錯誤

確認服務帳戶具有以下權限：

- Cloud Run Admin
- Cloud Build Editor
- Artifact Registry Writer
- Service Account User

檢查權限：

```bash
gcloud projects get-iam-policy sales-ai-automation-v2 \
  --flatten="bindings[].members" \
  --filter="bindings.members:497329205771-compute@developer.gserviceaccount.com"
```

### 品質檢查失敗

如果品質檢查失敗，部署不會執行。請：

1. 查看 Actions 日誌中的錯誤訊息
2. 在本地修復錯誤
3. 使用 `/deploy` 命令驗證修復
4. 重新推送到 main

## 進階配置

### 使用 Workload Identity Federation（推薦）

為了更好的安全性，建議使用 Workload Identity Federation 代替服務帳戶金鑰：

1. 設置 Workload Identity Pool
2. 配置 GitHub OIDC provider
3. 更新 workflow 使用 `workload_identity_provider`

參考: [Google Cloud 官方文檔](https://github.com/google-github-actions/auth#setup)

### 環境特定部署

如需支援多個環境（dev, staging, production），可以：

1. 為每個環境創建不同的 workflow
2. 使用環境特定的 secrets
3. 根據分支名稱選擇部署目標

## 相關文檔

- [QUICK_START_FOR_AI.md](/QUICK_START_FOR_AI.md) - AI 助理快速上手指南
- [git-deploy-checker agent](/.claude/agents/git-deploy-checker.md) - 本地部署檢查邏輯
- [GitHub Actions 文檔](https://docs.github.com/en/actions)
- [google-github-actions/auth](https://github.com/google-github-actions/auth)
