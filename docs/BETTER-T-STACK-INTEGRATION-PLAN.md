# Better-T Stack 整合部署計劃

> **版本**: 1.0
> **建立日期**: 2026-01-08
> **目標**: 整合 Better-T Stack 前端架構，支援多 Agent 平行開發

---

## 📋 目錄

1. [整合架構總覽](#整合架構總覽)
2. [Agent 分工設計](#agent-分工設計)
3. [介面契約定義](#介面契約定義)
4. [平行開發工作流程](#平行開發工作流程)
5. [Phase 實施計劃](#phase-實施計劃)
6. [目錄結構變更](#目錄結構變更)
7. [部署策略](#部署策略)

---

## 整合架構總覽

### 整合後系統架構

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Better-T Stack 前端層                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │   Dashboard     │  │   Admin Panel   │  │   Mobile (未來)         │  │
│  │   (Agent G)     │  │   (Agent H)     │  │   (Agent I)             │  │
│  └────────┬────────┘  └────────┬────────┘  └────────────────────────┘  │
│           │                    │                                        │
│           └────────────────────┼────────────────────────────────────────┤
│                                │                                        │
│                    ┌───────────▼───────────┐                           │
│                    │   API Client Layer    │                           │
│                    │   (OpenAPI Generated) │                           │
│                    │   packages/api-client │                           │
│                    └───────────┬───────────┘                           │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │ Type-safe HTTP (OpenAPI)
┌────────────────────────────────┼────────────────────────────────────────┐
│                     API Gateway Layer                                    │
│                    ┌───────────▼───────────┐                           │
│                    │   FastAPI Gateway     │                           │
│                    │   (Agent A 負責)      │                           │
│                    │   /api/v1/*           │                           │
│                    └───────────┬───────────┘                           │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────────────┐
│                    現有 Python 後端服務                                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ Module  │  │ Module  │  │ Module  │  │ Module  │  │ Module  │       │
│  │   01    │  │   02    │  │   03    │  │   04/05 │  │   06    │       │
│  │(Agent B)│  │(Agent C)│  │(Agent D)│  │(Agent E)│  │(Agent F)│       │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │
│       └────────────┴────────────┴────────────┴────────────┘            │
│                                 │                                       │
│                    ┌────────────▼────────────┐                         │
│                    │      Firestore          │                         │
│                    │   (共用資料層)           │                         │
│                    └─────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent 分工設計

### Agent 總覽表

| Agent | 負責範圍 | 技術棧 | 可修改路徑 | 依賴 |
|-------|---------|--------|-----------|------|
| **A** | Core + Infra + API Gateway | Python/FastAPI | `core/`, `infrastructure/`, `api-gateway/` | - |
| **B** | Lead Source | Python | `modules/01-lead-source/` | A |
| **C** | MQL Qualification | Python | `modules/02-mql-qualification/` | A |
| **D** | Sales Conversation | Python | `modules/03-sales-conversation/`, `integrations/slack/` | A |
| **E** | Deal + CS | Python | `modules/04-deal-onboarding/`, `modules/05-customer-success/` | A |
| **F** | Analytics Backend | Python | `modules/06-analytics/` | A |
| **G** | Dashboard Frontend | TypeScript | `dashboard/apps/web/` | A (API) |
| **H** | Admin Panel Frontend | TypeScript | `dashboard/apps/admin/` | A (API) |
| **I** | Shared UI Components | TypeScript | `dashboard/packages/ui/`, `dashboard/packages/api-client/` | - |

### Agent 依賴關係圖

```
                    ┌─────────────────┐
                    │    Agent A      │
                    │  (Core + API)   │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │  Agent I    │    │ Python      │    │ Python      │
   │  (Shared)   │    │ Agents      │    │ Agents      │
   │             │    │ B, C, D     │    │ E, F        │
   └──────┬──────┘    └─────────────┘    └─────────────┘
          │
   ┌──────┴──────┐
   │             │
   ▼             ▼
┌─────────┐  ┌─────────┐
│ Agent G │  │ Agent H │
│(Dashboard) │(Admin)  │
└─────────┘  └─────────┘
```

### 各 Agent 詳細職責

#### Agent A - Core + Infrastructure + API Gateway

```markdown
# Agent A - Core & API Gateway

## 職責
1. FastAPI Gateway 開發與維護
2. OpenAPI Schema 定義
3. Core 介面與模型
4. 部署腳本與 CI/CD

## 產出物
- `/api-gateway/` - FastAPI 應用
- `/api-gateway/openapi.json` - API 規格（供前端使用）
- `/core/schemas/` - Pydantic 模型
- `/infrastructure/` - 部署配置

## 關鍵介面
- 產出 OpenAPI Schema 供 Agent G, H, I 使用
- 定義所有 API 端點規格
```

#### Agent G - Dashboard Frontend

```markdown
# Agent G - Dashboard Frontend

## 職責
1. 銷售經理儀表板開發
2. 對話分析視覺化
3. 即時數據展示

## 技術棧
- TanStack Router (路由)
- TanStack Query (資料獲取)
- shadcn/ui + Tailwind (UI)
- Recharts (圖表)

## 依賴
- 使用 Agent I 產出的 `@sales-ai/ui` 組件
- 使用 Agent I 產出的 `@sales-ai/api-client` 呼叫 API

## 可修改路徑
- `dashboard/apps/web/src/**`
- `dashboard/apps/web/package.json`
```

#### Agent H - Admin Panel Frontend

```markdown
# Agent H - Admin Panel Frontend

## 職責
1. 系統管理介面
2. Agent 配置管理
3. 成本監控儀表板

## 依賴
- 使用 Agent I 產出的共用組件

## 可修改路徑
- `dashboard/apps/admin/src/**`
- `dashboard/apps/admin/package.json`
```

#### Agent I - Shared Packages

```markdown
# Agent I - Shared UI & API Client

## 職責
1. 共用 UI 組件庫
2. API Client 自動生成
3. 共用類型定義

## 產出物
- `@sales-ai/ui` - 共用 UI 組件
- `@sales-ai/api-client` - 類型安全 API 客戶端
- `@sales-ai/types` - 共用類型

## 關鍵任務
- 監聽 Agent A 的 OpenAPI Schema 變更
- 自動重新生成 API Client
```

---

## 介面契約定義

### API 契約 (Agent A ↔ Agent G/H/I)

```yaml
# api-gateway/openapi.yaml (由 Agent A 維護)

openapi: 3.1.0
info:
  title: Sales AI Automation API
  version: 2.0.0

paths:
  /api/v1/conversations:
    get:
      operationId: listConversations
      summary: 列出對話記錄
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [pending, analyzing, completed, failed]
        - name: limit
          in: query
          schema:
            type: integer
            default: 50
      responses:
        '200':
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Conversation'

  /api/v1/conversations/{id}:
    get:
      operationId: getConversation
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ConversationDetail'

  /api/v1/conversations/{id}/analysis:
    get:
      operationId: getAnalysis
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnalysisResult'

  /api/v1/leads:
    get:
      operationId: listLeads
      responses:
        '200':
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Lead'

  /api/v1/analytics/dashboard:
    get:
      operationId: getDashboardStats
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DashboardStats'

components:
  schemas:
    Conversation:
      type: object
      required: [id, status, createdAt]
      properties:
        id:
          type: string
        leadId:
          type: string
        salesRepName:
          type: string
        status:
          type: string
          enum: [pending, transcribing, analyzing, completed, failed]
        conversationType:
          type: string
        createdAt:
          type: string
          format: date-time
        completedAt:
          type: string
          format: date-time

    ConversationDetail:
      allOf:
        - $ref: '#/components/schemas/Conversation'
        - type: object
          properties:
            transcript:
              $ref: '#/components/schemas/Transcript'
            analysis:
              $ref: '#/components/schemas/AnalysisResult'

    AnalysisResult:
      type: object
      properties:
        contextData:
          type: object
        buyerData:
          type: object
        sellerCoaching:
          type: object
        meddicScore:
          type: integer
        summary:
          type: string

    Lead:
      type: object
      properties:
        id:
          type: string
        email:
          type: string
        name:
          type: string
        company:
          type: string
        status:
          type: string
        score:
          type: integer
        createdAt:
          type: string
          format: date-time

    DashboardStats:
      type: object
      properties:
        totalConversations:
          type: integer
        completedToday:
          type: integer
        avgMeddicScore:
          type: number
        conversionRate:
          type: number
        topPerformers:
          type: array
          items:
            type: object
```

### 事件契約 (跨 Agent 通知)

```python
# core/interfaces/events.py (由 Agent A 維護)

class IntegrationEvent(str, Enum):
    """跨 Agent 整合事件"""

    # API Schema 變更事件 (Agent A → Agent I)
    OPENAPI_SCHEMA_UPDATED = "openapi.schema.updated"

    # 資料變更事件 (Python Agents → Dashboard)
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_UPDATED = "conversation.updated"
    ANALYSIS_COMPLETED = "analysis.completed"
    LEAD_CREATED = "lead.created"
    LEAD_UPDATED = "lead.updated"

    # 告警事件
    COACH_ALERT_TRIGGERED = "coach.alert.triggered"
```

---

## 平行開發工作流程

### 開發流程圖

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Phase 1: 基礎建設                                │
│                                                                          │
│   ┌─────────────┐                              ┌─────────────┐          │
│   │  Agent A    │                              │  Agent I    │          │
│   │             │                              │             │          │
│   │ 1. FastAPI  │──── OpenAPI Schema ─────────▶│ 1. 初始化   │          │
│   │    Gateway  │                              │    專案結構  │          │
│   │             │                              │             │          │
│   │ 2. 定義     │                              │ 2. 建立     │          │
│   │    Schemas  │                              │    UI 組件  │          │
│   └─────────────┘                              └─────────────┘          │
│                                                                          │
│   Python Agents (B-F): 維持現狀，無需變更                                  │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          Phase 2: 平行開發                                │
│                                                                          │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│   │  Agent A    │    │  Agent G    │    │  Agent H    │                 │
│   │             │    │             │    │             │                 │
│   │ 持續維護    │    │ Dashboard   │    │ Admin       │                 │
│   │ API 端點    │    │ 頁面開發    │    │ 頁面開發    │                 │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│          │                  │                  │                        │
│          │    ┌─────────────┴──────────────────┘                        │
│          │    │                                                         │
│          │    ▼                                                         │
│          │   ┌─────────────┐                                            │
│          │   │  Agent I    │                                            │
│          │   │             │                                            │
│          └──▶│ API Client  │◀── 共用組件                                │
│              │ 自動生成    │                                            │
│              └─────────────┘                                            │
│                                                                          │
│   Python Agents (B-F): 獨立開發各模組功能                                  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 同步開發規則

#### 規則 1: API Schema 變更流程

```bash
# Agent A 修改 API 後的流程

1. Agent A 修改 FastAPI 端點
   └── 自動更新 openapi.json

2. CI/CD 觸發 webhook
   └── 通知 Agent I

3. Agent I 執行
   └── bun run generate:api-client
   └── 更新 @sales-ai/api-client

4. Agent G, H 自動獲得新類型
   └── TypeScript 編譯檢查
```

#### 規則 2: 分支策略

```
main
├── develop
│   │
│   ├── feature/api-gateway          # Agent A
│   ├── feature/api-conversations    # Agent A
│   │
│   ├── feature/dashboard-home       # Agent G
│   ├── feature/dashboard-analytics  # Agent G
│   │
│   ├── feature/admin-settings       # Agent H
│   │
│   ├── feature/ui-components        # Agent I
│   ├── feature/api-client-v2        # Agent I
│   │
│   ├── feature/sales-meddic-v2      # Agent D (Python)
│   └── feature/analytics-funnel     # Agent F (Python)
│
└── release/v2.1.0
```

#### 規則 3: 合併順序

```
合併優先級（由高到低）:

1. Agent A (Core/API) - 最高優先，其他 Agent 依賴
   ↓
2. Agent I (Shared)   - UI 組件和 API Client
   ↓
3. Agent G, H (Apps)  - 應用層，最後合併

4. Agent B-F (Python) - 獨立合併，不影響前端
```

### Agent 啟動指令

#### Agent A - Core + API Gateway

```bash
cd ~/sales-ai-automation-V2
claude

# Prompt:
"""
我是 Agent A，負責 Core、Infrastructure 和 API Gateway 開發。

## 我的職責
1. FastAPI Gateway (`api-gateway/`)
2. OpenAPI Schema 定義
3. Core 介面和模型 (`core/`)
4. 部署配置 (`infrastructure/`)

## 本次任務
- 建立 FastAPI Gateway
- 定義 API 端點
- 產出 openapi.json

## 我不能修改
- `modules/` 目錄
- `dashboard/` 目錄（除了讀取）
- `.claude/skills/` 其他 Agent 的設定

請先讀取 docs/BETTER-T-STACK-INTEGRATION-PLAN.md 了解整體規劃。
"""
```

#### Agent G - Dashboard Frontend

```bash
cd ~/sales-ai-automation-V2/dashboard/apps/web
claude

# Prompt:
"""
我是 Agent G，負責 Dashboard 前端開發。

## 我的職責
1. 銷售經理儀表板
2. 對話分析視覺化
3. 即時數據展示

## 技術棧
- TanStack Router (路由)
- TanStack Query (資料獲取)
- shadcn/ui + Tailwind (UI)

## 我的依賴
- `@sales-ai/ui` - 共用 UI 組件（Agent I 維護）
- `@sales-ai/api-client` - API 客戶端（Agent I 維護）

## 我只能修改
- `dashboard/apps/web/src/**`
- `dashboard/apps/web/package.json`

## 我不能修改
- `dashboard/packages/` (由 Agent I 負責)
- `api-gateway/` (由 Agent A 負責)
- Python 相關目錄

請先讀取 docs/BETTER-T-STACK-INTEGRATION-PLAN.md 了解 API 契約。
"""
```

#### Agent I - Shared Packages

```bash
cd ~/sales-ai-automation-V2/dashboard
claude

# Prompt:
"""
我是 Agent I，負責共用 UI 組件和 API Client。

## 我的職責
1. `packages/ui/` - shadcn/ui 共用組件
2. `packages/api-client/` - OpenAPI 自動生成客戶端
3. `packages/types/` - 共用 TypeScript 類型

## 關鍵任務
當 Agent A 更新 `api-gateway/openapi.json` 時：
1. 執行 `bun run generate:api-client`
2. 更新 `packages/api-client/`
3. 通知 Agent G, H 有新版本

## 我只能修改
- `dashboard/packages/**`
- `dashboard/turbo.json`
- `dashboard/package.json`

## 我不能修改
- `dashboard/apps/` (由 Agent G, H 負責)
- Python 相關目錄

請先讀取 docs/BETTER-T-STACK-INTEGRATION-PLAN.md。
"""
```

---

## Phase 實施計劃

### Phase 1: 基礎建設 (Week 1-2)

```
┌────────────────────────────────────────────────────────────────┐
│ Week 1: API Gateway + 專案初始化                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Agent A (並行)              Agent I (並行)                    │
│  ┌──────────────────┐       ┌──────────────────┐              │
│  │ Day 1-2:         │       │ Day 1-2:         │              │
│  │ - FastAPI 初始化  │       │ - Better-T Stack │              │
│  │ - 基本端點設計    │       │   專案初始化     │              │
│  │                  │       │ - Turborepo 設定  │              │
│  ├──────────────────┤       ├──────────────────┤              │
│  │ Day 3-4:         │       │ Day 3-4:         │              │
│  │ - Conversation   │       │ - UI 組件庫初始化│              │
│  │   API 端點       │       │ - shadcn/ui 設定 │              │
│  │ - OpenAPI 產出   │       │                  │              │
│  ├──────────────────┤       ├──────────────────┤              │
│  │ Day 5:           │       │ Day 5:           │              │
│  │ - 整合測試       │──────▶│ - API Client     │              │
│  │                  │       │   生成           │              │
│  └──────────────────┘       └──────────────────┘              │
│                                                                │
│  Python Agents (B-F): 無需變更，持續現有開發                    │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ Week 2: 核心 API 完成                                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Agent A                    Agent I                            │
│  ┌──────────────────┐       ┌──────────────────┐              │
│  │ - Lead API       │       │ - 完善 UI 組件   │              │
│  │ - Analytics API  │       │ - Table, Card    │              │
│  │ - Dashboard API  │       │ - Chart 組件     │              │
│  │ - Auth 中間件    │       │                  │              │
│  └──────────────────┘       └──────────────────┘              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### Phase 1 產出物

| Agent | 產出物 | 驗收標準 |
|-------|-------|---------|
| A | `api-gateway/` FastAPI 應用 | 所有端點可用，OpenAPI 可存取 |
| A | `api-gateway/openapi.json` | 符合 OpenAPI 3.1 規格 |
| I | `dashboard/` Monorepo 結構 | Turborepo 可正常建構 |
| I | `@sales-ai/api-client` | 可從 OpenAPI 生成類型 |
| I | `@sales-ai/ui` | 基礎組件可用 |

---

### Phase 2: Dashboard 開發 (Week 3-4)

```
┌────────────────────────────────────────────────────────────────┐
│ Week 3-4: 平行開發 Dashboard                                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Agent A          Agent G           Agent H        Agent I    │
│  ┌──────────┐    ┌──────────┐     ┌──────────┐   ┌──────────┐│
│  │ API 維護  │    │ 首頁     │     │ 設定頁   │   │ 組件支援 ││
│  │ 新增端點  │    │ 對話列表 │     │ Agent 管理│   │ 即時更新 ││
│  │          │    │ 分析詳情 │     │ 成本監控 │   │          ││
│  └──────────┘    └──────────┘     └──────────┘   └──────────┘│
│       │               │                │              │       │
│       └───────────────┴────────────────┴──────────────┘       │
│                              │                                 │
│                    ┌─────────▼─────────┐                      │
│                    │   Daily Sync      │                      │
│                    │   整合測試        │                      │
│                    └───────────────────┘                      │
│                                                                │
│  Python Agents: 獨立開發，API 透過 Gateway 暴露                 │
└────────────────────────────────────────────────────────────────┘
```

#### Phase 2 產出物

| Agent | 產出物 | 驗收標準 |
|-------|-------|---------|
| G | Dashboard 首頁 | 可顯示即時統計數據 |
| G | 對話列表頁 | 可列出、搜尋對話 |
| G | 對話詳情頁 | 可顯示分析結果 |
| H | 系統設定頁 | 可配置系統參數 |
| H | Agent 管理頁 | 可查看 Agent 狀態 |

---

### Phase 3: 整合部署 (Week 5-6)

```
┌────────────────────────────────────────────────────────────────┐
│ Week 5-6: 整合與部署                                            │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    整合任務                               │  │
│  │                                                         │  │
│  │  1. Dashboard + API Gateway 整合測試                     │  │
│  │  2. Firestore 即時訂閱整合                               │  │
│  │  3. 認證流程整合 (GCP IAM / Slack OAuth)                 │  │
│  │  4. 效能測試與優化                                       │  │
│  │  5. 部署到 Cloud Run                                    │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  部署架構:                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │ Cloud Run   │    │ Cloud Run   │    │ Firebase    │       │
│  │ Dashboard   │───▶│ API Gateway │───▶│ Hosting     │       │
│  │ (SSR/靜態)  │    │ (FastAPI)   │    │ (可選)      │       │
│  └─────────────┘    └─────────────┘    └─────────────┘       │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 目錄結構變更

### 變更後完整結構

```
sales-ai-automation-V2/
│
├── 📁 api-gateway/                          # 🆕 FastAPI Gateway (Agent A)
│   ├── __init__.py
│   ├── main.py                              # FastAPI 主程式
│   ├── config.py                            # 設定
│   ├── 📁 routers/                          # API 路由
│   │   ├── __init__.py
│   │   ├── conversations.py                 # /api/v1/conversations
│   │   ├── leads.py                         # /api/v1/leads
│   │   ├── analytics.py                     # /api/v1/analytics
│   │   └── health.py                        # /api/v1/health
│   ├── 📁 schemas/                          # Pydantic Response Models
│   │   ├── __init__.py
│   │   ├── conversation.py
│   │   ├── lead.py
│   │   └── analytics.py
│   ├── 📁 middleware/                       # 中間件
│   │   ├── __init__.py
│   │   ├── auth.py                          # 認證
│   │   ├── cors.py                          # CORS
│   │   └── logging.py                       # 請求日誌
│   ├── openapi.json                         # 🔑 自動生成的 OpenAPI Schema
│   ├── Dockerfile
│   └── requirements.txt
│
├── 📁 dashboard/                            # 🆕 Better-T Stack 前端 (Agent G, H, I)
│   ├── package.json                         # Workspace 根設定
│   ├── turbo.json                           # Turborepo 設定
│   ├── 📁 apps/
│   │   ├── 📁 web/                          # Dashboard App (Agent G)
│   │   │   ├── package.json
│   │   │   ├── vite.config.ts
│   │   │   ├── 📁 src/
│   │   │   │   ├── main.tsx
│   │   │   │   ├── 📁 routes/               # TanStack Router 頁面
│   │   │   │   │   ├── __root.tsx
│   │   │   │   │   ├── index.tsx            # 首頁
│   │   │   │   │   ├── 📁 conversations/
│   │   │   │   │   │   ├── index.tsx        # 列表
│   │   │   │   │   │   └── $id.tsx          # 詳情
│   │   │   │   │   ├── 📁 leads/
│   │   │   │   │   │   └── index.tsx
│   │   │   │   │   └── 📁 analytics/
│   │   │   │   │       └── index.tsx
│   │   │   │   ├── 📁 components/           # 頁面專用組件
│   │   │   │   ├── 📁 hooks/                # 自訂 Hooks
│   │   │   │   └── 📁 lib/                  # 工具函式
│   │   │   └── index.html
│   │   │
│   │   └── 📁 admin/                        # Admin App (Agent H)
│   │       ├── package.json
│   │       └── 📁 src/
│   │           └── ... (類似結構)
│   │
│   └── 📁 packages/                         # 共用套件 (Agent I)
│       ├── 📁 ui/                           # UI 組件庫
│       │   ├── package.json
│       │   └── 📁 src/
│       │       ├── index.ts
│       │       ├── 📁 components/
│       │       │   ├── button.tsx
│       │       │   ├── card.tsx
│       │       │   ├── data-table.tsx
│       │       │   ├── chart.tsx
│       │       │   └── ...
│       │       └── 📁 styles/
│       │           └── globals.css
│       │
│       ├── 📁 api-client/                   # API 客戶端
│       │   ├── package.json
│       │   ├── 📁 src/
│       │   │   ├── index.ts
│       │   │   ├── client.ts                # openapi-fetch 客戶端
│       │   │   └── schema.d.ts              # 🔑 從 OpenAPI 生成
│       │   └── scripts/
│       │       └── generate.ts              # 類型生成腳本
│       │
│       └── 📁 types/                        # 共用類型
│           ├── package.json
│           └── 📁 src/
│               └── index.ts
│
├── 📁 core/                                 # 現有 (Agent A)
├── 📁 modules/                              # 現有 (Agent B-F)
├── 📁 integrations/                         # 現有
├── 📁 infrastructure/                       # 現有 (Agent A)
│   ├── 📁 docker/
│   │   ├── Dockerfile.api-gateway           # 🆕
│   │   ├── Dockerfile.dashboard             # 🆕
│   │   └── ... (現有)
│   └── 📁 cloudbuild/
│       ├── api-gateway.yaml                 # 🆕
│       ├── dashboard.yaml                   # 🆕
│       └── ... (現有)
│
├── 📁 docs/
│   ├── BETTER-T-STACK-INTEGRATION-PLAN.md   # 🆕 本文件
│   └── ... (現有)
│
└── 📁 .claude/
    └── 📁 skills/
        ├── 📁 00-core-skill/                # 更新
        ├── 📁 07-dashboard-skill/           # 🆕 Agent G
        │   └── SKILL.md
        ├── 📁 08-admin-skill/               # 🆕 Agent H
        │   └── SKILL.md
        └── 📁 09-shared-packages-skill/     # 🆕 Agent I
            └── SKILL.md
```

---

## 部署策略

### Cloud Run 部署架構

```yaml
# infrastructure/cloudbuild/deploy-all.yaml

steps:
  # 1. 建構 API Gateway
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/api-gateway', '-f', 'api-gateway/Dockerfile', '.']
    id: 'build-api-gateway'

  # 2. 建構 Dashboard (可平行)
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/dashboard', '-f', 'infrastructure/docker/Dockerfile.dashboard', './dashboard']
    id: 'build-dashboard'
    waitFor: ['-']  # 不等待，平行執行

  # 3. 推送映像
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/api-gateway']
    waitFor: ['build-api-gateway']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/dashboard']
    waitFor: ['build-dashboard']

  # 4. 部署到 Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'api-gateway'
      - '--image=gcr.io/$PROJECT_ID/api-gateway'
      - '--region=asia-east1'
      - '--platform=managed'
      - '--allow-unauthenticated'
    waitFor: ['push-api-gateway']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'dashboard'
      - '--image=gcr.io/$PROJECT_ID/dashboard'
      - '--region=asia-east1'
      - '--platform=managed'
      - '--allow-unauthenticated'
```

### 環境變數配置

```yaml
# API Gateway 環境變數
API_GATEWAY_ENV:
  FIRESTORE_DATABASE: "(default)"
  GCP_PROJECT_ID: "sales-ai-automation-v2"
  CORS_ORIGINS: "https://dashboard.sales-ai.example.com"
  LOG_LEVEL: "INFO"

# Dashboard 環境變數
DASHBOARD_ENV:
  VITE_API_URL: "https://api-gateway-xxx.asia-east1.run.app"
  VITE_FIREBASE_CONFIG: "..."
```

---

## 附錄: 快速開始腳本

### 初始化腳本

```bash
#!/bin/bash
# scripts/init-better-t-stack.sh

set -e

echo "🚀 初始化 Better-T Stack 整合..."

# 1. 建立 API Gateway
echo "📦 建立 API Gateway..."
mkdir -p api-gateway/{routers,schemas,middleware}
touch api-gateway/{__init__,main,config}.py
touch api-gateway/requirements.txt

# 2. 建立 Dashboard Monorepo
echo "📦 初始化 Dashboard..."
cd "$(dirname "$0")/.."
mkdir -p dashboard

cd dashboard
bun create better-t-stack@latest . \
  --frontend tanstack-router \
  --backend none \
  --no-auth \
  --addons turborepo \
  --yes

# 3. 建立 packages 結構
echo "📦 建立共用套件..."
mkdir -p packages/{ui,api-client,types}/src

# 4. 安裝 OpenAPI 工具
cd packages/api-client
bun add openapi-fetch
bun add -D openapi-typescript

# 5. 建立 API Client 生成腳本
cat > scripts/generate.ts << 'EOF'
import { execSync } from 'child_process';
const OPENAPI_URL = process.env.OPENAPI_URL || '../../api-gateway/openapi.json';
execSync(`bunx openapi-typescript ${OPENAPI_URL} -o src/schema.d.ts`);
console.log('✅ API Client types generated');
EOF

echo "✅ 初始化完成！"
echo ""
echo "下一步："
echo "1. Agent A: cd api-gateway && 開始建立 FastAPI 端點"
echo "2. Agent I: cd dashboard && bun install && bun run dev"
echo "3. Agent G: cd dashboard/apps/web && 開始開發頁面"
```

---

## 總結

本計劃設計了一個支援 **9 個 Agent 平行開發** 的架構：

| 類型 | Agent | 數量 |
|------|-------|------|
| Python 後端 | A (Core), B-F (Modules) | 6 |
| TypeScript 前端 | G (Dashboard), H (Admin), I (Shared) | 3 |

### 關鍵成功因素

1. **清晰的介面契約**: OpenAPI Schema 作為前後端唯一真相來源
2. **自動化類型生成**: API 變更自動同步到前端
3. **獨立的可部署單元**: 每個服務獨立部署，互不影響
4. **Daily Sync 機制**: 每日整合測試，及早發現問題

---

*文件版本：1.0*
*最後更新：2026-01-08*
