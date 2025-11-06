# AI Collaboration Playbook

> 為所有語言模型與開發者提供一致的開發邏輯、作業順序與紀錄方式，確保跨模型交接順暢。

---

## 🧭 核心原則

1. **憲法優先**：所有實作須符合 `memory/constitution.md`（特別是 VII. Activity Logging & Traceability）。  
2. **開發前先對齊**：閱讀最新現況（Quick Start、Development Log、Outstanding Work Tracker）。  
3. **透明紀錄**：每次行動都在 `DEVELOPMENT_LOG.md` 留下可追溯紀錄，並更新待辦勾選。  
4. **可驗證輸出**：程式碼變更需搭配測試或驗證說明；部署與設定更新要寫明指令與結果。  
5. **交接即完成**：Session 結束前送出使用者摘要＋更新紀錄＋核對 checklist，避免資訊遺失。

---

## 🔄 標準作業流程（SOP）

### 0. 進場準備

- 查看 `QUICK_START_FOR_AI.md` → 確認當前階段/進度。  
- 閱讀 `DEVELOPMENT_GUIDELINES.md` Rule 1-7（錄入規則、PR Checklist）。  
- 詳讀 `DEVELOPMENT_LOG.md` 最近一次 Session、Outstanding Work Tracker。  
- 確認必要憑證取得方式：`docs/credential-management.md`。

### 1. 分析與規劃

- 若任務複雜，使用工作計畫工具（/plan）列出步驟。  
- 明確列出要修改的檔案與預期輸出（文件、程式、測試、部署設定）。

### 2. 執行階段

1. **資料蒐集**：閱讀 specs/plan/task 文件或現有程式碼。  
2. **實作**：依優先順序完成程式或文檔更新；必要時建立工具函式。  
3. **測試/驗證**：執行單元測試或 CLI 指令；若無法測試須註明原因與風險。  
4. **同步說明**：在開發過程中記錄關鍵決策、前置條件或阻塞因素（便於後續補寫 Log）。

### 3. Session 收尾

1. **更新開發日誌**：  
   - 新增/更新 Session 條目：模型、日期、主要產出、測試結果、待辦。  
   - 將完成的事項在 Outstanding Work Tracker 勾選（附檔案路徑／行號）。  
2. **檢查 Checklist**：使用 `docs/checklists/pr.md` 自我核對；尚未完成者寫明原因。  
3. **撰寫使用者摘要**：整理變更重點、測試結果、下一步建議。  
4. **確認憑證/機密**：清除臨時 `.env` 或記錄補充（若涉及 Secret 更新）。

---

## 🗂️ 紀錄與交接模板

### Development Log Session 範例

```markdown
### Session X: 2025-11-05 (任務標題)
- **模型**: Codex CLI（GPT-5）
- **重點輸出**:
  - 更新檔案與目的
  - 新增測試或部署指令
  - 決策/風險說明
- **驗證／紀錄**:
  - 測試指令與結果（或無法測試的理由）
  - 已更新 Outstanding Work Tracker 對應項目

#### Next Session Preparation
- 待辦項目與阻塞因素
- 必要參考文件或環境設定
```

### 使用者 Session 摘要

```markdown
- 完成事項：列出核心變更與對應檔案
- 測試紀錄：命令 / 結果 / 失敗原因
- 決策與風險：重點說明
- 下一步建議：數項具體行動
```

---

## 🔐 憑證與環境設定

- 所有金鑰/Token 皆由 Secret Manager 管理，取得方式參考 `docs/credential-management.md`。  
- 新增或使用 Secrets 時，記得在日誌標註來源、用途與更新步驟。  
- `.env` 僅供本地測試，請勿提交；Session 結束後清除或移除關聯記錄。

---

## 🧪 測試與驗證準則

- 優先執行與修改內容相關的單元/整合測試。  
- 若需新增測試，命名與結構需遵循既有模式。  
- 測試指令與結果（含失敗原因）需寫入 `DEVELOPMENT_LOG.md`。  
- 無法測試時，在日誌與使用者摘要說明阻礙與風險。

---

## 🗣️ 溝通約定

- **語言**：使用繁體中文（除代碼或 API 名稱）。  
- **引用**：附上檔案路徑與行號（`path/to/file.py:123`）或測試輸出。  
- **決策回報**：重大決策/偏離憲法需記錄於日誌並在使用者摘要標註。  
- **阻塞處理**：遇到環境或權限問題，於日誌與摘要中清楚描述影響範圍與建議。

---

## 📎 相關文件

- `DEVELOPMENT_GUIDELINES.md`：詳細錄入規則、PR Checklist、決策紀錄範例。  
- `DEVELOPMENT_LOG.md`：唯一權威的開發歷史與 Outstanding Tracker。  
- `QUICK_START_FOR_AI.md`：新進模型必讀的專案導覽。  
- `docs/credential-management.md`：Secrets、Token 取得與管理方式。  
- `docs/checklists/pr.md`：提交前的核對清單。

> 若對流程有改進建議，請在 `DEVELOPMENT_LOG.md` 記錄並提議更新此 Playbook。
