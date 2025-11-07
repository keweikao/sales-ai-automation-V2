# Pull Request Checklist

每位貢獻者（含所有語言模型）在提交 PR 或任何形式的變更審查前，請逐項確認以下事項。未勾選的項目視為流程未完成，審查者可直接退回。

## 📄 紀錄與治理

- [ ] 已依 `memory/constitution.md:89` 的「Activity Logging & Traceability」原則更新 `DEVELOPMENT_LOG.md`（新增 session 或補充現有紀錄），並記載負責模型、產出內容與待辦。
- [ ] 若本次變更涉及待辦完成，已同步更新 `DEVELOPMENT_LOG.md:39` 的 📌 Outstanding Work Tracker（勾選完成並附上證據，如檔案行號、測試結果、部署記錄）。
- [ ] 若建立額外活動紀錄（例如 `docs/activity-log/`），已在 `DEVELOPMENT_LOG.md` 摘要與連結。

## 🧪 程式碼與測試

- [ ] 已執行必要的單元／整合／端對端測試，並在 PR 敘述中紀錄測試命令與結果；若無法測試，已書面說明原因與風險。
- [ ] 所有新建或修改檔案遵循專案格式與命名規範；新增程式碼（非自明者）已補上必要註解或文件。

## 🚀 部署與設定（如適用）

- [ ] 若涉及部署、環境變數或秘密管理，已更新相關文件（例如 `agent8-phase1-deployment.md`、`installation.md`），並在 `DEVELOPMENT_LOG.md` 記錄驗證步驟與結果。
- [ ] 已確認 CI/CD 或手動部署腳本成功執行，並保留操作紀錄。

## 📢 溝通

- [ ] PR 描述清楚列出變更重點、影響範圍、風險與回滾方案。
- [ ] 已通知受影響的利害關係人（例如 Slack 頻道、指定 reviewers），並在紀錄中標註。

> ✅ 勾選所有適用項目後方可提交 PR。若流程由語言模型執行，應於最終回覆中附上已完成項目的明細與對應紀錄位置。
