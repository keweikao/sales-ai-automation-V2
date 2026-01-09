# V2/V3 功能同步清單

本文件追蹤 V2 已完成的功能，以及對應的 V3 實作狀態。

---

## 功能狀態說明

| 狀態 | 說明 |
|------|------|
| ✅ | V3 已實作 |
| 🔄 | V3 開發中 |
| ⏳ | 待實作 |
| ➖ | 不需要遷移 |

---

## 核心功能

### 1. 認證與授權

| V2 功能 | V2 檔案 | V3 狀態 | V3 Agent | 備註 |
|---------|---------|---------|----------|------|
| Google OAuth 登入 | `api-gateway/routers/auth.py` | ⏳ | D | Better-Auth 實作 |
| Session 管理 | `api-gateway/routers/auth.py` | ⏳ | D | Better-Auth 內建 |
| 角色權限 | `core/auth/` | ⏳ | D | 評估是否需要 |

### 2. Lead 管理

| V2 功能 | V2 檔案 | V3 狀態 | V3 Agent | 備註 |
|---------|---------|---------|----------|------|
| Lead CRUD | `api-gateway/routers/leads.py` | ⏳ | D | oRPC router |
| Lead 狀態流轉 | `core/leads/` | ⏳ | D | 參考 `shared/schemas/lead.yaml` |
| Lead 評分 | `modules/02-lead-scoring/` | ⏳ | D | AI 評分邏輯 |
| Lead 匯入 | `api-gateway/routers/leads.py` | ⏳ | D | CSV/Excel 匯入 |

### 3. 對話管理

| V2 功能 | V2 檔案 | V3 狀態 | V3 Agent | 備註 |
|---------|---------|---------|----------|------|
| 對話 CRUD | `api-gateway/routers/conversations.py` | ⏳ | D | 參考 `shared/schemas/conversation.yaml` |
| 對話記錄 | `core/conversations/` | ⏳ | D | 儲存到 PostgreSQL |
| 對話分析 | `modules/03-sales-conversation/` | ⏳ | D | MEDDIC 分析 |

### 4. MEDDIC 分析

| V2 功能 | V2 檔案 | V3 狀態 | V3 Agent | 備註 |
|---------|---------|---------|----------|------|
| Agent 1: Context | `modules/03-.../meddic/agents/agent1_context.py` | ⏳ | D | 使用 `shared/prompts/meddic/agent1-context.md` |
| Agent 2: Buyer | `modules/03-.../meddic/agents/agent2_buyer.py` | ⏳ | D | 使用 `shared/prompts/meddic/agent2-buyer.md` |
| Agent 3: Seller | `modules/03-.../meddic/agents/agent3_seller.py` | ⏳ | D | 使用 `shared/prompts/meddic/agent3-seller.md` |
| Agent 4: Summary | `modules/03-.../meddic/agents/agent4_summary.py` | ⏳ | D | 使用 `shared/prompts/meddic/agent4-summary.md` |
| Agent 6: CRM | `modules/03-.../meddic/agents/agent6_crm_extractor.py` | ⏳ | D | 使用 `shared/prompts/meddic/agent6-crm-extractor.md` |
| Multi-Agent 協調 | `modules/03-.../meddic/multi_agent_meddic.py` | ⏳ | D | 流程編排 |

### 5. 外部服務整合

| V2 功能 | V2 檔案 | V3 狀態 | V3 Agent | 備註 |
|---------|---------|---------|----------|------|
| Gemini LLM | `core/llm/gemini_client.py` | ⏳ | C | TypeScript SDK |
| 語音轉文字 | `modules/01-transcription/` | ⏳ | C | Google/Deepgram |
| GCS 儲存 | `core/storage/gcs_client.py` | ⏳ | C | 評估 Cloudflare R2 |
| Salesforce 整合 | `modules/05-salesforce/` | ⏳ | C | jsforce |

### 6. Slack Bot

| V2 功能 | V2 檔案 | V3 狀態 | V3 Agent | 備註 |
|---------|---------|---------|----------|------|
| Slack Commands | `modules/04-slack-bot/` | ⏳ | F | @slack/bolt |
| 訊息通知 | `modules/04-slack-bot/notifications.py` | ⏳ | F | 事件驅動 |
| 對話互動 | `modules/04-slack-bot/handlers/` | ⏳ | F | Block Kit UI |

### 7. 排程任務

| V2 功能 | V2 檔案 | V3 狀態 | V3 Agent | 備註 |
|---------|---------|---------|----------|------|
| 定時報表 | `modules/07-ops-automation/` | ⏳ | G | Cloudflare Cron |
| 資料同步 | `modules/07-ops-automation/` | ⏳ | G | 背景任務 |

### 8. UI 元件

| V2 功能 | V2 檔案 | V3 狀態 | V3 Agent | 備註 |
|---------|---------|---------|----------|------|
| Lead Table | `ui/src/components/LeadTable.tsx` | ⏳ | B | shadcn/ui |
| Conversation View | `ui/src/components/ConversationView.tsx` | ⏳ | B | 重新設計 |
| MEDDIC Dashboard | `ui/src/components/MEDDICDashboard.tsx` | ⏳ | B | 視覺化改進 |
| Analytics Charts | `ui/src/components/charts/` | ⏳ | B | Recharts |

---

## 前端頁面

| V2 頁面 | V2 路由 | V3 狀態 | V3 Agent | 備註 |
|---------|---------|---------|----------|------|
| 首頁 | `/` | ⏳ | E | 儀表板 |
| Lead 列表 | `/leads` | ⏳ | E | 分頁、篩選 |
| Lead 詳情 | `/leads/:id` | ⏳ | E | 整合對話 |
| 對話列表 | `/conversations` | ⏳ | E | 時間軸檢視 |
| 對話詳情 | `/conversations/:id` | ⏳ | E | MEDDIC 分析結果 |
| 分析報表 | `/analytics` | ⏳ | E | 圖表視覺化 |
| 設定 | `/settings` | ⏳ | E | 使用者偏好 |

---

## 資料模型

| 模型 | V2 來源 | V3 狀態 | Schema 檔案 |
|------|---------|---------|-------------|
| Lead | Firestore | ⏳ | `shared/schemas/lead.yaml` |
| Conversation | Firestore | ⏳ | `shared/schemas/conversation.yaml` |
| MEDDIC Analysis | Firestore | ⏳ | `shared/schemas/meddic.yaml` |
| User | Firestore | ⏳ | Agent A 定義 |
| Session | - | ⏳ | Better-Auth 內建 |

---

## 同步規則

### 1. Prompt 變更
- 直接在 `shared/prompts/` 修改
- 提交到 V2 repo
- V3 啟動時自動載入

### 2. Schema 變更
- 更新 `shared/schemas/*.yaml`
- 執行 `shared/scripts/sync-to-v3.sh`（V3 建立後）
- V3 重新生成 TypeScript 類型

### 3. 業務規則變更
- 更新 `shared/docs/` 相關文檔
- 更新對應的 YAML schema
- 通知相關 Agent 更新實作

---

## 變更記錄

| 日期 | 變更內容 | 負責人 |
|------|----------|--------|
| 2025-01-09 | 建立初始功能清單 | Claude |

