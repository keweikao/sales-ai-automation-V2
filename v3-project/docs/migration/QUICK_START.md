# V3 遷移快速啟動指南

## 📊 並行開發總覽

```
                    Phase 0 (人工)
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐
    │ Agent A │     │ Agent B │     │ Agent C │     Phase 1
    │Database │     │   UI    │     │Services │     (並行)
    └────┬────┘     └────┬────┘     └────┬────┘
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐
    │ Agent D │     │ Agent E │     │ Agent F │     Phase 2
    │   API   │     │Frontend │     │  Slack  │     (並行)
    └────┬────┘     └────┬────┘     └────┬────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
                    ┌─────────┐
                    │ Agent G │                      Phase 3
                    │Integrate│
                    └────┬────┘
                         │
                         ▼
                    ┌─────────┐
                    │ Agent H │                      Phase 4
                    │Migration│
                    └────┬────┘
                         │
                         ▼
                    ┌─────────┐
                    │ Agent I │                      Phase 5
                    │ Deploy  │
                    └─────────┘
```

## 🚀 執行步驟

### Phase 0：專案初始化（人工執行）

```bash
cd /home/user

# 建立新專案
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

# 確認可運行
cd Sales_ai_automation_v3
bun run dev
```

### Phase 1：並行執行 Agent A, B, C

同時啟動三個 Agent，各自獨立工作：

| Agent | Prompt 檔案 | 任務 |
|-------|-------------|------|
| A | `agent-prompts/AGENT_A_DATABASE.md` | 建立 Drizzle Schema |
| B | `agent-prompts/AGENT_B_UI.md` | 遷移 UI 元件 |
| C | `agent-prompts/AGENT_C_SERVICES.md` | 建立外部服務整合 |

**同步點檢查**：
```bash
ls Sales_ai_automation_v3/packages/db/AGENT_A_COMPLETE.md
ls Sales_ai_automation_v3/packages/ui/AGENT_B_COMPLETE.md
ls Sales_ai_automation_v3/apps/server/src/services/AGENT_C_COMPLETE.md
```

### Phase 2：並行執行 Agent D, E, F

等待 Phase 1 完成後，同時啟動：

| Agent | 依賴 | Prompt 檔案 | 任務 |
|-------|------|-------------|------|
| D | A 完成 | `agent-prompts/AGENT_D_API.md` | 建立 API Routers |
| E | B 完成 | `agent-prompts/AGENT_E_FRONTEND.md` | 遷移前端頁面 |
| F | C 完成 | `agent-prompts/AGENT_F_SLACK.md` | 建立 Slack Bot |

**同步點檢查**：
```bash
ls Sales_ai_automation_v3/apps/server/src/routers/AGENT_D_COMPLETE.md
ls Sales_ai_automation_v3/apps/web/src/routes/AGENT_E_COMPLETE.md
ls Sales_ai_automation_v3/apps/server/src/slack/AGENT_F_COMPLETE.md
```

### Phase 3：執行 Agent G

等待 Phase 2 完成後執行：

| Agent | 依賴 | Prompt 檔案 | 任務 |
|-------|------|-------------|------|
| G | D, E, F 完成 | `agent-prompts/AGENT_G_INTEGRATION.md` | 整合所有模組 |

**驗證**：
```bash
cd Sales_ai_automation_v3
bun run dev
# 確認前後端都能正常啟動
curl http://localhost:3000/health
```

### Phase 4：執行 Agent H

| Agent | 依賴 | Prompt 檔案 | 任務 |
|-------|------|-------------|------|
| H | G 完成 | `agent-prompts/AGENT_H_MIGRATION.md` | 資料遷移腳本 |

### Phase 5：執行 Agent I

| Agent | 依賴 | Prompt 檔案 | 任務 |
|-------|------|-------------|------|
| I | H 完成 | `agent-prompts/AGENT_I_DEPLOYMENT.md` | 部署配置 |

---

## 📁 檔案結構

```
docs/migration/
├── V3_MIGRATION_PLAN.md          # 完整遷移計劃
├── QUICK_START.md                # 本文件
└── agent-prompts/                # Agent Prompt 檔案
    ├── AGENT_A_DATABASE.md
    ├── AGENT_B_UI.md
    ├── AGENT_C_SERVICES.md
    ├── AGENT_D_API.md
    ├── AGENT_E_FRONTEND.md
    ├── AGENT_F_SLACK.md
    ├── AGENT_G_INTEGRATION.md
    ├── AGENT_H_MIGRATION.md
    └── AGENT_I_DEPLOYMENT.md
```

---

## ⏱️ 預估時程

| 執行方式 | 總時間 |
|----------|--------|
| 序列執行 | ~22 小時 |
| 並行執行 | ~12 小時 |

**節省 45% 時間！**

---

## 🎯 Agent 使用方式

每個 Agent Prompt 檔案可以直接複製給 AI Agent（如 Claude、ChatGPT）執行。

### 範例：啟動 Agent A

1. 開啟 `agent-prompts/AGENT_A_DATABASE.md`
2. 複製全部內容
3. 貼到 AI Agent 對話中
4. Agent 會自動執行任務
5. 完成後檢查 `AGENT_A_COMPLETE.md` 是否存在

### 並行執行提示

可以同時開啟多個 AI Agent 視窗，各自執行不同的任務：

```
視窗 1: Agent A (Database)
視窗 2: Agent B (UI)
視窗 3: Agent C (Services)
```

---

## ✅ 完成檢查清單

```
Phase 0:
□ 新專案建立成功
□ bun run dev 可啟動

Phase 1:
□ AGENT_A_COMPLETE.md 存在
□ AGENT_B_COMPLETE.md 存在
□ AGENT_C_COMPLETE.md 存在

Phase 2:
□ AGENT_D_COMPLETE.md 存在
□ AGENT_E_COMPLETE.md 存在
□ AGENT_F_COMPLETE.md 存在

Phase 3:
□ AGENT_G_COMPLETE.md 存在
□ 前後端可正常啟動
□ API 可正常呼叫

Phase 4:
□ AGENT_H_COMPLETE.md 存在
□ 遷移腳本可執行

Phase 5:
□ AGENT_I_COMPLETE.md 存在
□ 部署成功
□ 生產環境可存取
```

---

## 🆘 問題排解

### Agent 執行失敗

1. 檢查前置條件是否滿足
2. 檢查對應的 `AGENT_X_COMPLETE.md` 是否有錯誤說明
3. 修復問題後重新執行該 Agent

### 整合問題

由 Agent G (Integration) 負責處理所有整合問題。

### 部署問題

參考 `docs/DEPLOYMENT.md` 或 Agent I 的完成報告。
