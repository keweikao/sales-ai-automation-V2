# Sales AI Automation V3 遷移計劃

## 並行開發執行指南

本文件設計為可以讓多個 AI Agent 同時並行開發，加速遷移過程。

---

## 📊 任務依賴圖

```
                                    ┌─────────────────┐
                                    │   Phase 0       │
                                    │   專案初始化     │
                                    │   (人工執行)     │
                                    └────────┬────────┘
                                             │
                     ┌───────────────────────┼───────────────────────┐
                     │                       │                       │
                     ▼                       ▼                       ▼
            ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
            │   Agent A      │     │   Agent B      │     │   Agent C      │
            │   Database     │     │   UI/Frontend  │     │   External     │
            │   Schema       │     │   Components   │     │   Services     │
            └───────┬────────┘     └───────┬────────┘     └───────┬────────┘
                    │                      │                      │
                    │              ┌───────┴───────┐              │
                    │              │               │              │
                    ▼              ▼               │              ▼
            ┌────────────────┐  ┌────────────────┐ │    ┌────────────────┐
            │   Agent D      │  │   Agent E      │ │    │   Agent F      │
            │   API Routers  │  │   Frontend     │ │    │   Slack Bot    │
            │   (依賴 A)     │  │   Pages        │ │    │   (依賴 C)     │
            └───────┬────────┘  │   (依賴 B)     │ │    └───────┬────────┘
                    │           └───────┬────────┘ │            │
                    │                   │          │            │
                    └─────────┬─────────┴──────────┼────────────┘
                              │                    │
                              ▼                    │
                    ┌────────────────┐             │
                    │   Agent G      │             │
                    │   Integration  │◄────────────┘
                    │   (依賴 D,E,F) │
                    └───────┬────────┘
                            │
                            ▼
                    ┌────────────────┐
                    │   Agent H      │
                    │   Data         │
                    │   Migration    │
                    └───────┬────────┘
                            │
                            ▼
                    ┌────────────────┐
                    │   Agent I      │
                    │   Deployment   │
                    │   & Testing    │
                    └────────────────┘
```

---

## 🚀 Phase 0：專案初始化（人工執行）

**執行者**：人工
**前置條件**：無

```bash
# 1. 建立新專案
cd /home/user
bun create better-t-stack@latest Sales_ai_automation_v3 \
  --frontend tanstack-router \
  --backend hono \
  --runtime bun \
  --api orpc \
  --auth better-auth \
  --payments none \
  --database postgres \
  --orm drizzle \
  --db-setup neon \
  --package-manager bun \
  --git \
  --web-deploy cloudflare \
  --server-deploy cloudflare \
  --install \
  --addons biome turborepo ultracite \
  --examples none

# 2. 設定環境變數
cd Sales_ai_automation_v3
cp .env.example .env
# 填入必要的 API keys

# 3. 確認專案可運行
bun install
bun run dev
```

**完成標準**：
- [ ] 新專案建立成功
- [ ] `bun run dev` 可正常啟動
- [ ] Neon 資料庫連線成功

---

## 🤖 Phase 1：並行開發（Agent A, B, C 同時執行）

### Agent A：Database Schema

**可並行**：是（無依賴）
**預估時間**：2-3 小時

#### Agent A Prompt

```
你是 Database Schema Agent，負責在 Sales_ai_automation_v3 專案中建立 Drizzle ORM schema。

## 你的任務

1. 閱讀舊專案的資料結構：
   - /home/user/sales-ai-automation-V2/core/schemas/lead.py
   - /home/user/sales-ai-automation-V2/core/schemas/conversation.py
   - /home/user/sales-ai-automation-V2/api-gateway/schemas/conversation.py
   - /home/user/sales-ai-automation-V2/api-gateway/schemas/analytics.py

2. 在新專案建立 Drizzle schema：
   - /home/user/Sales_ai_automation_v3/packages/db/src/schema/leads.ts
   - /home/user/Sales_ai_automation_v3/packages/db/src/schema/conversations.ts
   - /home/user/Sales_ai_automation_v3/packages/db/src/schema/sales-reps.ts
   - /home/user/Sales_ai_automation_v3/packages/db/src/schema/analytics.ts
   - /home/user/Sales_ai_automation_v3/packages/db/src/schema/index.ts (導出所有)

3. 建立必要的 enum 類型：
   - lead_source: squarespace, linkedin, referral, website, event, cold_outreach, other
   - lead_status: new, contacted, mql, sql, opportunity, negotiation, closed_won, closed_lost
   - conversation_status: pending, transcribing, analyzing, completed, failed

4. 建立關聯：
   - conversations.leadId -> leads.id
   - conversations.salesRepId -> salesReps.id

5. 執行 migration：
   - 運行 `bun run db:generate`
   - 運行 `bun run db:push`

## 輸出要求

完成後在 /home/user/Sales_ai_automation_v3/packages/db/AGENT_A_COMPLETE.md 建立完成報告，包含：
- 建立的 tables 列表
- 每個 table 的欄位說明
- 關聯關係圖
- Migration 執行結果

## 技術規範

- 使用 Drizzle ORM 語法
- 使用 PostgreSQL 資料類型
- 所有 timestamp 使用 UTC
- JSON 欄位使用 jsonb 類型
- 主鍵使用 varchar(255) 或 uuid
```

---

### Agent B：UI Components

**可並行**：是（無依賴）
**預估時間**：2-3 小時

#### Agent B Prompt

```
你是 UI Components Agent，負責將 UI 元件從舊專案遷移到新專案。

## 你的任務

1. 複製並調整 UI 元件：
   - 來源：/home/user/sales-ai-automation-V2/dashboard/packages/ui/src/
   - 目標：/home/user/Sales_ai_automation_v3/packages/ui/src/

2. 確保元件相容性：
   - 調整 import paths
   - 確保使用 Biome 格式化
   - 移除未使用的依賴

3. 建立以下共用元件（如果不存在）：
   - Button, Card, Input, Select, Dialog
   - Table, Pagination
   - Loading, Error, Empty states
   - Charts (如果有使用)

4. 建立元件導出：
   - /home/user/Sales_ai_automation_v3/packages/ui/src/index.ts

5. 確保樣式一致：
   - 使用 Tailwind CSS
   - 保持原有設計風格

## 輸出要求

完成後在 /home/user/Sales_ai_automation_v3/packages/ui/AGENT_B_COMPLETE.md 建立完成報告，包含：
- 遷移的元件列表
- 新增的元件列表
- 修改說明
- 使用範例

## 技術規範

- 使用 React 18+ 語法
- 使用 TypeScript strict mode
- 使用 Tailwind CSS
- 元件需要有 TypeScript props 定義
```

---

### Agent C：External Services

**可並行**：是（無依賴）
**預估時間**：2-3 小時

#### Agent C Prompt

```
你是 External Services Agent，負責建立外部服務整合層。

## 你的任務

1. 閱讀舊專案的服務整合：
   - /home/user/sales-ai-automation-V2/core/llm/client.py
   - /home/user/sales-ai-automation-V2/infrastructure/services/transcription/
   - /home/user/sales-ai-automation-V2/modules/03-sales-conversation/slack_bot/

2. 在新專案建立服務層：

   a. LLM Service (/home/user/Sales_ai_automation_v3/apps/server/src/services/llm.ts)
      - 使用 @google/generative-ai 套件
      - 實作 generate() 和 generateStructured() 方法
      - 支援 Gemini 2.0 Flash 模型

   b. Transcription Service (/home/user/Sales_ai_automation_v3/apps/server/src/services/transcription.ts)
      - 使用 groq-sdk 套件
      - 實作 transcribe() 方法
      - 支援 whisper-large-v3 模型

   c. Storage Service (/home/user/Sales_ai_automation_v3/apps/server/src/services/storage.ts)
      - 使用 @aws-sdk/client-s3 (R2 相容)
      - 實作 uploadAudio(), getAudio(), deleteAudio()

   d. 服務導出 (/home/user/Sales_ai_automation_v3/apps/server/src/services/index.ts)

3. 建立環境變數類型定義：
   - /home/user/Sales_ai_automation_v3/apps/server/src/env.ts

## 輸出要求

完成後在 /home/user/Sales_ai_automation_v3/apps/server/src/services/AGENT_C_COMPLETE.md 建立完成報告，包含：
- 各服務的 API 說明
- 環境變數需求列表
- 使用範例
- 錯誤處理說明

## 技術規範

- 使用 async/await
- 實作適當的錯誤處理
- 添加 TypeScript 類型定義
- 使用 zod 驗證環境變數
```

---

## 🤖 Phase 2：依賴開發（Agent D, E, F）

### Agent D：API Routers

**前置條件**：Agent A 完成
**可並行**：與 Agent E, F 並行
**預估時間**：3-4 小時

#### Agent D Prompt

```
你是 API Routers Agent，負責建立 oRPC API 端點。

## 前置條件檢查

確認 Agent A 已完成：
- 檢查 /home/user/Sales_ai_automation_v3/packages/db/AGENT_A_COMPLETE.md 存在
- 確認 schema 檔案已建立

## 你的任務

1. 閱讀舊專案的 API：
   - /home/user/sales-ai-automation-V2/api-gateway/routers/conversations.py
   - /home/user/sales-ai-automation-V2/api-gateway/routers/leads.py
   - /home/user/sales-ai-automation-V2/api-gateway/routers/analytics.py
   - /home/user/sales-ai-automation-V2/api-gateway/routers/health.py

2. 在新專案建立 oRPC routers：

   a. Health Router (/home/user/Sales_ai_automation_v3/apps/server/src/routers/health.ts)
      - health.check: 健康檢查端點

   b. Conversations Router (/home/user/Sales_ai_automation_v3/apps/server/src/routers/conversations.ts)
      - conversations.list: 列出對話（支援篩選）
      - conversations.getById: 取得單一對話
      - conversations.getAnalysis: 取得分析結果
      - conversations.create: 建立新對話
      - conversations.updateStatus: 更新狀態

   c. Leads Router (/home/user/Sales_ai_automation_v3/apps/server/src/routers/leads.ts)
      - leads.list: 列出潛客
      - leads.getById: 取得單一潛客
      - leads.getByEmail: 用 email 查詢
      - leads.create: 建立潛客
      - leads.updateStatus: 更新狀態
      - leads.updateScore: 更新分數

   d. Analytics Router (/home/user/Sales_ai_automation_v3/apps/server/src/routers/analytics.ts)
      - analytics.dashboard: 儀表板統計
      - analytics.trends: 趨勢資料
      - analytics.weeklyReport: 週報
      - analytics.repStats: 業務員統計

   e. 主 Router (/home/user/Sales_ai_automation_v3/apps/server/src/routers/index.ts)
      - 導出 appRouter 和 AppRouter 類型

3. 使用 Drizzle ORM 進行資料庫操作

## 輸出要求

完成後在 /home/user/Sales_ai_automation_v3/apps/server/src/routers/AGENT_D_COMPLETE.md 建立完成報告，包含：
- API 端點列表
- 每個端點的 input/output schema
- 使用範例

## 技術規範

- 使用 @orpc/server
- 使用 zod 進行輸入驗證
- 使用 Drizzle ORM 查詢
- 實作適當的錯誤處理
```

---

### Agent E：Frontend Pages

**前置條件**：Agent B 完成
**可並行**：與 Agent D, F 並行
**預估時間**：3-4 小時

#### Agent E Prompt

```
你是 Frontend Pages Agent，負責遷移前端頁面並整合 oRPC client。

## 前置條件檢查

確認 Agent B 已完成：
- 檢查 /home/user/Sales_ai_automation_v3/packages/ui/AGENT_B_COMPLETE.md 存在
- 確認 UI 元件已建立

## 你的任務

1. 設定 oRPC Client：
   - /home/user/Sales_ai_automation_v3/apps/web/src/lib/api.ts

2. 閱讀並遷移舊專案頁面：
   - 來源：/home/user/sales-ai-automation-V2/dashboard/apps/web/src/routes/

3. 建立以下頁面：

   a. Dashboard (/home/user/Sales_ai_automation_v3/apps/web/src/routes/index.tsx)
      - 顯示統計數據
      - 顯示最近對話
      - 顯示趨勢圖表

   b. Conversations List (/home/user/Sales_ai_automation_v3/apps/web/src/routes/conversations/index.tsx)
      - 對話列表
      - 篩選功能
      - 分頁

   c. Conversation Detail (/home/user/Sales_ai_automation_v3/apps/web/src/routes/conversations/$id.tsx)
      - 對話詳情
      - 逐字稿顯示
      - 分析結果

   d. Leads List (/home/user/Sales_ai_automation_v3/apps/web/src/routes/leads/index.tsx)
      - 潛客列表
      - 篩選功能

   e. Analytics (/home/user/Sales_ai_automation_v3/apps/web/src/routes/analytics/index.tsx)
      - 趨勢圖表
      - 業務員表現

4. 設定 TanStack Router：
   - /home/user/Sales_ai_automation_v3/apps/web/src/routes/__root.tsx
   - /home/user/Sales_ai_automation_v3/apps/web/src/routeTree.gen.ts

## 輸出要求

完成後在 /home/user/Sales_ai_automation_v3/apps/web/src/routes/AGENT_E_COMPLETE.md 建立完成報告，包含：
- 頁面列表和路由
- 使用的 UI 元件
- oRPC 查詢列表

## 技術規範

- 使用 TanStack Router
- 使用 oRPC React hooks
- 使用 packages/ui 的元件
- 實作 loading 和 error 狀態
```

---

### Agent F：Slack Bot

**前置條件**：Agent C 完成
**可並行**：與 Agent D, E 並行
**預估時間**：3-4 小時

#### Agent F Prompt

```
你是 Slack Bot Agent，負責建立 Slack Bot 整合。

## 前置條件檢查

確認 Agent C 已完成：
- 檢查 /home/user/Sales_ai_automation_v3/apps/server/src/services/AGENT_C_COMPLETE.md 存在
- 確認外部服務已建立

## 你的任務

1. 閱讀舊專案的 Slack Bot：
   - /home/user/sales-ai-automation-V2/modules/03-sales-conversation/slack_bot/

2. 在新專案建立 Slack Bot：

   a. Slack App 初始化 (/home/user/Sales_ai_automation_v3/apps/server/src/slack/app.ts)
      - 使用 @slack/bolt
      - 設定 Socket Mode

   b. Event Handlers (/home/user/Sales_ai_automation_v3/apps/server/src/slack/handlers/file-upload.ts)
      - 監聽 file_shared 事件
      - 處理音檔上傳
      - 觸發轉錄和分析流程

   c. Message Handlers (/home/user/Sales_ai_automation_v3/apps/server/src/slack/handlers/messages.ts)
      - 處理使用者訊息
      - 回應查詢指令

   d. Blocks Builder (/home/user/Sales_ai_automation_v3/apps/server/src/slack/blocks/analysis-result.ts)
      - 建立分析結果的 Slack Block Kit 訊息

   e. 整合到主服務 (/home/user/Sales_ai_automation_v3/apps/server/src/slack/index.ts)

3. 建立處理流程：
   - 音檔上傳 → 轉錄 → 分析 → 發送結果

## 輸出要求

完成後在 /home/user/Sales_ai_automation_v3/apps/server/src/slack/AGENT_F_COMPLETE.md 建立完成報告，包含：
- 支援的事件列表
- 支援的指令列表
- Block Kit 訊息格式
- 處理流程圖

## 技術規範

- 使用 @slack/bolt
- 使用 Socket Mode
- 使用 Agent C 建立的服務
- 實作適當的錯誤處理和重試
```

---

## 🤖 Phase 3：整合（Agent G）

### Agent G：Integration

**前置條件**：Agent D, E, F 全部完成
**預估時間**：2-3 小時

#### Agent G Prompt

```
你是 Integration Agent，負責整合所有模組並確保系統正常運作。

## 前置條件檢查

確認以下 Agent 已完成：
- Agent D: /home/user/Sales_ai_automation_v3/apps/server/src/routers/AGENT_D_COMPLETE.md
- Agent E: /home/user/Sales_ai_automation_v3/apps/web/src/routes/AGENT_E_COMPLETE.md
- Agent F: /home/user/Sales_ai_automation_v3/apps/server/src/slack/AGENT_F_COMPLETE.md

## 你的任務

1. 整合後端服務：
   - 更新 /home/user/Sales_ai_automation_v3/apps/server/src/index.ts
   - 整合 oRPC routers
   - 整合 Slack Bot
   - 設定 CORS
   - 設定錯誤處理中間件

2. 整合前端：
   - 確認 oRPC client 正確連接後端
   - 確認所有頁面可正常存取 API

3. 建立完整處理流程：
   - /home/user/Sales_ai_automation_v3/apps/server/src/workflows/analyze-conversation.ts
   - 整合：上傳 → 轉錄 → LLM 分析 → 儲存 → 通知

4. 建立 E2E 測試：
   - /home/user/Sales_ai_automation_v3/tests/e2e/conversation-flow.test.ts

5. 修復任何整合問題

## 輸出要求

完成後在 /home/user/Sales_ai_automation_v3/AGENT_G_COMPLETE.md 建立完成報告，包含：
- 整合架構圖
- API 端點完整列表
- 已知問題和解決方案
- 測試結果

## 驗證清單

- [ ] `bun run dev` 可正常啟動前後端
- [ ] 前端可正確呼叫後端 API
- [ ] Slack Bot 可正常接收事件
- [ ] 完整流程可執行
```

---

## 🤖 Phase 4：資料遷移（Agent H）

### Agent H：Data Migration

**前置條件**：Agent G 完成
**預估時間**：2-3 小時

#### Agent H Prompt

```
你是 Data Migration Agent，負責將資料從 Firestore 遷移到 PostgreSQL。

## 前置條件檢查

確認 Agent G 已完成：
- 檢查 /home/user/Sales_ai_automation_v3/AGENT_G_COMPLETE.md 存在

## 你的任務

1. 建立遷移腳本：

   a. 主遷移腳本 (/home/user/Sales_ai_automation_v3/scripts/migrate-data.ts)
      - 連接 Firestore（使用舊專案的 credentials）
      - 連接 PostgreSQL（使用新專案的 DATABASE_URL）
      - 遷移 leads collection
      - 遷移 sales_cases collection
      - 遷移 cases collection（分析資料）

   b. 驗證腳本 (/home/user/Sales_ai_automation_v3/scripts/validate-migration.ts)
      - 比對記錄數量
      - 抽樣驗證資料完整性
      - 驗證關聯正確性

   c. 回滾腳本 (/home/user/Sales_ai_automation_v3/scripts/rollback-migration.ts)
      - 清空 PostgreSQL 資料
      - 保留 Firestore 資料不動

2. 資料轉換邏輯：
   - Firestore timestamp → PostgreSQL timestamp
   - Nested objects → JSONB
   - Array fields → JSON string 或 JSONB

3. 建立遷移指南：
   - /home/user/Sales_ai_automation_v3/docs/MIGRATION_GUIDE.md

## 輸出要求

完成後在 /home/user/Sales_ai_automation_v3/scripts/AGENT_H_COMPLETE.md 建立完成報告，包含：
- 遷移腳本說明
- 資料對應表
- 執行步驟
- 驗證結果（如果有測試資料）

## 技術規範

- 使用 @google-cloud/firestore
- 使用 Drizzle ORM 寫入
- 實作 batch 處理（每 500 筆一批）
- 實作 progress logging
- 實作錯誤重試機制
```

---

## 🤖 Phase 5：部署（Agent I）

### Agent I：Deployment & Testing

**前置條件**：Agent H 完成
**預估時間**：2-3 小時

#### Agent I Prompt

```
你是 Deployment Agent，負責設定部署配置和執行最終測試。

## 前置條件檢查

確認 Agent H 已完成：
- 檢查 /home/user/Sales_ai_automation_v3/scripts/AGENT_H_COMPLETE.md 存在

## 你的任務

1. Cloudflare Workers 配置：
   - 更新 /home/user/Sales_ai_automation_v3/apps/server/wrangler.toml
   - 設定環境變數 bindings
   - 設定 R2 bucket binding
   - 設定 secrets

2. Cloudflare Pages 配置：
   - 更新前端建置設定
   - 設定環境變數

3. 建立 CI/CD：
   - /home/user/Sales_ai_automation_v3/.github/workflows/deploy.yml
   - 自動化測試
   - 自動化部署

4. 建立健康檢查：
   - /home/user/Sales_ai_automation_v3/apps/server/src/health.ts

5. 建立監控設定：
   - 錯誤追蹤
   - 效能監控

6. 編寫部署文檔：
   - /home/user/Sales_ai_automation_v3/docs/DEPLOYMENT.md

## 輸出要求

完成後在 /home/user/Sales_ai_automation_v3/AGENT_I_COMPLETE.md 建立完成報告，包含：
- 部署架構圖
- 環境變數列表
- 部署步驟
- 監控設定

## 部署驗證清單

- [ ] Workers 部署成功
- [ ] Pages 部署成功
- [ ] API 健康檢查通過
- [ ] 前端可正常載入
- [ ] Slack Bot 可正常運作
```

---

## 📋 並行執行總覽

```
時間軸 →

Phase 0 (人工)
████████

Phase 1 (並行)
         Agent A ████████
         Agent B ████████
         Agent C ████████

Phase 2 (並行，等待 Phase 1)
                          Agent D ████████████
                          Agent E ████████████
                          Agent F ████████████

Phase 3 (等待 Phase 2)
                                              Agent G ████████

Phase 4 (等待 Phase 3)
                                                        Agent H ████████

Phase 5 (等待 Phase 4)
                                                                  Agent I ████████
```

---

## 🔄 同步點與檢查

### 同步點 1：Phase 1 完成

檢查以下檔案存在：
- `/home/user/Sales_ai_automation_v3/packages/db/AGENT_A_COMPLETE.md`
- `/home/user/Sales_ai_automation_v3/packages/ui/AGENT_B_COMPLETE.md`
- `/home/user/Sales_ai_automation_v3/apps/server/src/services/AGENT_C_COMPLETE.md`

### 同步點 2：Phase 2 完成

檢查以下檔案存在：
- `/home/user/Sales_ai_automation_v3/apps/server/src/routers/AGENT_D_COMPLETE.md`
- `/home/user/Sales_ai_automation_v3/apps/web/src/routes/AGENT_E_COMPLETE.md`
- `/home/user/Sales_ai_automation_v3/apps/server/src/slack/AGENT_F_COMPLETE.md`

### 同步點 3：Phase 3 完成

檢查以下檔案存在：
- `/home/user/Sales_ai_automation_v3/AGENT_G_COMPLETE.md`

驗證系統：
```bash
cd /home/user/Sales_ai_automation_v3
bun run dev
# 確認前後端都能正常啟動
```

### 同步點 4：Phase 4 完成

檢查以下檔案存在：
- `/home/user/Sales_ai_automation_v3/scripts/AGENT_H_COMPLETE.md`

### 同步點 5：Phase 5 完成

檢查以下檔案存在：
- `/home/user/Sales_ai_automation_v3/AGENT_I_COMPLETE.md`

---

## 📊 Agent 執行總表

| Agent | 任務 | 依賴 | 可並行 | 預估時間 |
|-------|------|------|--------|----------|
| A | Database Schema | 無 | Phase 1 | 2-3 hr |
| B | UI Components | 無 | Phase 1 | 2-3 hr |
| C | External Services | 無 | Phase 1 | 2-3 hr |
| D | API Routers | A | Phase 2 | 3-4 hr |
| E | Frontend Pages | B | Phase 2 | 3-4 hr |
| F | Slack Bot | C | Phase 2 | 3-4 hr |
| G | Integration | D, E, F | 單獨 | 2-3 hr |
| H | Data Migration | G | 單獨 | 2-3 hr |
| I | Deployment | H | 單獨 | 2-3 hr |

**總預估時間**：
- 序列執行：~22 小時
- 並行執行：~12 小時（節省 45%）

---

## 🚨 錯誤處理

如果任何 Agent 失敗：

1. 檢查對應的 `AGENT_X_COMPLETE.md` 是否有錯誤說明
2. 修復問題後重新執行該 Agent
3. 確認完成後再繼續下一階段

## 📝 注意事項

1. 每個 Agent 完成後必須建立完成報告
2. 完成報告是下一階段的前置條件檢查
3. Agent 之間不直接通訊，透過檔案系統同步
4. 如遇到問題，在完成報告中記錄，由整合 Agent 處理
