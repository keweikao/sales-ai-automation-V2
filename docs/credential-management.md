# Credential & Secret Management Guide

> 🧭 目的：集中管理本專案使用的所有金鑰、Token 與憑證，確保每位語言模型或開發者都能在不重複索取的情況下存取既有憑證。

## 🎯 原則

- 所有敏感資訊一律儲存在 **GCP Secret Manager**（Production / Staging 環境）或受控的共享保管庫（例如 1Password business vault）；**不得**硬編在程式碼或 commit。
- 本地開發需透過 `gcloud secrets versions access` 匯出到 `.env` 或臨時檔案，並於 Session 結束後清除。
- 每次部署前，請確認所需 Secret 已存在並授權給對應的 Cloud Run / Cloud Functions 服務帳號。

---

## 🔑 Secrets 一覽表

| 服務 / 用途 | Secret Manager 名稱 | 環境變數 / 檔案 | 用途說明 |
|-------------|---------------------|------------------|----------|
| Slack Bot Token | `slack-bot-token` | `SLACK_BOT_TOKEN` | Slack 機器人 API 呼叫 |
| Slack Signing Secret | `slack-signing-secret` | `SLACK_SIGNING_SECRET` | Events API 驗證簽章 |
| Slack App Token (Socket Mode) | `slack-app-token` | `SLACK_APP_TOKEN` | Socket Mode 連線（若啟用） |
| Gemini API Key | `gemini-api-key` | `GEMINI_API_KEY` | Google Generative AI 呼叫 |
| GCP Service Account (JSON) | `sales-ai-service-account` | `GOOGLE_APPLICATION_CREDENTIALS` 指向下載檔 | Firestore / Storage / Tasks 權限 |
| Hugging Face Token | `huggingface-token` | `HUGGINGFACE_TOKEN` | Whisper 說話者辨識模型下載 |
| Twilio Account SID | `twilio-account-sid` | `TWILIO_ACCOUNT_SID` | SMS 通知 |
| Twilio Auth Token | `twilio-auth-token` | `TWILIO_AUTH_TOKEN` | SMS 通知 |
| Firestore 管理員清單 | `manager-slack-ids` | 匯出 JSON 供初始化 | Agent 8 主管權限設定 |
| Cloud Tasks OIDC Signing Key | `cloud-tasks-service-account` | 供部署腳本使用 | Cloud Tasks 呼叫後端驗證（若啟用） |

> 如需新增其他 Secret，請更新此表格並於 `DEVELOPMENT_LOG.md` 記錄。

---

## 📥 取得與注入 Secrets

### 1. 使用 Secret Manager CLI

```bash
gcloud secrets versions access latest --secret=slack-bot-token
gcloud secrets versions access latest --secret=gemini-api-key
```

若需大量匯出，可使用 `scripts/bash/export-secrets.sh`（未來若建立），或自行將輸出導向 `.secrets/` 目錄。

### 2. 建立 `.env`

1. 複製樣板：`cp .env.example .env`
2. 依照下列指令填入各項：

```bash
echo "SLACK_BOT_TOKEN=$(gcloud secrets versions access latest --secret=slack-bot-token)" >> .env
echo "SLACK_SIGNING_SECRET=$(gcloud secrets versions access latest --secret=slack-signing-secret)" >> .env
echo "GEMINI_API_KEY=$(gcloud secrets versions access latest --secret=gemini-api-key)" >> .env
echo "HUGGINGFACE_TOKEN=$(gcloud secrets versions access latest --secret=huggingface-token)" >> .env
```

3. 將 `.env` 加入 shell session：`export $(grep -v '^#' .env | xargs)`

> ⚠️ `.env` 僅供本地開發使用，請勿提交到版本控制；不用時刪除或搬移至安全位置。

### 3. Cloud Run / Cloud Functions

- 部署前以 `gcloud run services update` 或 Terraform 將 Secret 掛載為環境變數。
- 核對 `docs/agent8-phase1-deployment.md` 等部署文件，確保 `--set-secrets` 或 `--update-secrets` 指令使用上述名稱。

---

## 📤 分享流程（給新語言模型或開發者）

1. 在 `DEVELOPMENT_LOG.md` Session 條目中註記「Secrets 來源：Credential Management Guide」。
2. 提供對方 GCP 專案的角色（至少 `Secret Manager Secret Accessor`），或由管理者建立時間有限的 Service Account key。
3. 指引對方閱讀本文件，並確認 `.env` 是從 Secret Manager 匯出。

---

## ✅ 核對清單（每次 Session 結束前）

- [ ] 新增或使用的 Secret 是否已記錄在本文件表格？
- [ ] `.env` 是否已更新並在 `DEVELOPMENT_LOG.md` 註明？（若未修改則不需重複）
- [ ] 若部署到雲端，是否確認服務帳號具備讀取 Secret 權限？
- [ ] 是否於 PR Checklist 勾選「紀錄與治理」相關項目？

---

## 🔒 FAQ

**Q1. 可以把金鑰直接寫在 GitHub Action 或部署腳本嗎？**  
→ 不行，所有敏感資訊必須引用 Secret Manager。

**Q2. 如果 Secret 需要更新怎麼辦？**  
→ 由管理者在 Secret Manager 建立新版本 (`gcloud secrets versions add ...`)，並在 `DEVELOPMENT_LOG.md` 記錄更新原因與影響範圍。

**Q3. 本地無法使用 GCP CLI？**  
→ 由管理者提供加密的臨時檔案（例如 `.env.gpg`），或透過 1Password 共享，並仍在本文件與開發日誌記錄。
