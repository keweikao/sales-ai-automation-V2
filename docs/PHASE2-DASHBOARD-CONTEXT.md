# Phase 2: Dashboard 開發上下文

本文件提供給負責 Phase 2 (Dashboard 開發) 的 Agent 使用。

## 專案狀態

### 已完成 (Phase 0 + Phase 1 進行中)

1. **API Gateway 結構已建立**: `api-gateway/`
2. **Dashboard Monorepo 結構已建立**: `dashboard/`
3. **P0 阻塞問題已修復**:
   - Transcription Service 已連接
   - Notification Service (Slack) 已實作
   - Scheduler Jobs 已連接

---

## Dashboard 技術棧

```
dashboard/
├── apps/
│   ├── web/          # Agent G: 主 Dashboard
│   └── admin/        # Agent H: Admin Panel
├── packages/
│   ├── ui/           # @sales-ai/ui 共用組件
│   ├── api-client/   # @sales-ai/api-client
│   └── types/        # @sales-ai/types
├── package.json      # Bun + Turborepo
├── turbo.json
└── tsconfig.base.json
```

### 技術選擇
- **Runtime**: Bun
- **Monorepo**: Turborepo
- **Framework**: React (或 Better-T Stack 預設)
- **Styling**: Tailwind CSS
- **API Client**: openapi-fetch (從 OpenAPI 生成)

---

## API 端點清單

API Gateway 位於 `api-gateway/`，提供以下端點：

### Conversations API

```
GET  /api/v1/conversations
     Query params: status, sales_rep, start_date, end_date, limit, offset
     Response: ConversationListResponse

GET  /api/v1/conversations/{id}
     Response: ConversationDetail (含 transcript, analysis)

GET  /api/v1/conversations/{id}/analysis
     Response: AnalysisResult
```

### Analytics API

```
GET  /api/v1/analytics/dashboard
     Response: DashboardStats

GET  /api/v1/analytics/weekly-report
     Query params: week_start
     Response: WeeklyReportSummary

GET  /api/v1/analytics/trends
     Query params: period (7d, 30d, 90d)
     Response: AnalyticsTrends

GET  /api/v1/analytics/rep/{rep_id}
     Response: PerformerStats
```

### Health API

```
GET  /api/v1/health
     Response: { status: "healthy" }
```

---

## API Schema 定義

### Conversation Schema

```typescript
interface Conversation {
  id: string;
  leadId?: string;
  salesRepName?: string;
  status: 'pending' | 'transcribing' | 'analyzing' | 'completed' | 'failed';
  conversationType?: 'discovery' | 'demo' | 'negotiation' | 'follow_up' | 'closing';
  createdAt: string; // ISO datetime
  completedAt?: string;
}

interface ConversationListResponse {
  items: Conversation[];
  total: number;
  limit: number;
  offset: number;
}

interface TranscriptSegment {
  speaker?: string;
  text: string;
  start?: number; // seconds
  end?: number;
}

interface Transcript {
  segments: TranscriptSegment[];
  fullText?: string;
  language: string;
  durationSeconds?: number;
}

interface MEDDICData {
  metrics?: string;
  economicBuyer?: string;
  decisionCriteria?: string;
  decisionProcess?: string;
  identifyPain?: string;
  champion?: string;
}

interface BuyerData {
  identifiedNeeds: string[];
  hesitations: string[];
  painPoints: string[];
  trustScore?: number; // 0-100
  meddic?: MEDDICData;
}

interface CoachingInsight {
  category: 'strength' | 'improvement' | 'action';
  content: string;
  priority?: 'high' | 'medium' | 'low';
}

interface SellerCoaching {
  progressScore?: number; // 0-100
  recommendedStrategy?: string;
  insights: CoachingInsight[];
  nextSteps: string[];
}

interface AnalysisResult {
  contextData?: Record<string, any>;
  buyerData?: BuyerData;
  sellerCoaching?: SellerCoaching;
  meddicScore?: number; // 0-100
  summary?: string;
  customerSummary?: string;
  analyzedAt?: string;
}

interface ConversationDetail extends Conversation {
  transcript?: Transcript;
  analysis?: AnalysisResult;
  audioFileUri?: string;
  audioDurationSeconds?: number;
}
```

### Analytics Schema

```typescript
interface PerformerStats {
  id: string;
  name: string;
  conversationCount: number;
  avgMeddicScore: number;
  trend?: 'up' | 'down' | 'stable';
}

interface DashboardStats {
  totalConversations: number;
  completedToday: number;
  pendingAnalysis: number;
  avgMeddicScore: number;
  conversionRate: number;
  topPerformers: PerformerStats[];
  recentTrend?: 'improving' | 'declining' | 'stable';
  lastUpdated: string;
}

interface WeeklyReportSummary {
  periodStart: string;
  periodEnd: string;
  totalConversations: number;
  totalAnalyzed: number;
  avgMeddicScore: number;
  byRep: PerformerStats[];
  insights: string[];
  generatedAt: string;
}

interface TrendData {
  date: string;
  conversationCount: number;
  avgMeddicScore: number;
}

interface AnalyticsTrends {
  period: '7d' | '30d' | '90d';
  data: TrendData[];
  overallTrend: 'improving' | 'declining' | 'stable';
}
```

---

## Dashboard 頁面規劃

### Agent G: 主 Dashboard (`apps/web/`)

1. **首頁 `/`**
   - 統計卡片 (總對話數、今日完成、平均分數)
   - 最近對話列表
   - MEDDIC 分數趨勢圖

2. **對話列表 `/conversations`**
   - 篩選: 狀態、業務員、日期
   - 表格: ID、業務員、狀態、分數、時間
   - 點擊進入詳情

3. **對話詳情 `/conversations/:id`**
   - 基本資訊
   - 逐字稿播放器 (含時間軸)
   - MEDDIC 分析結果
   - 銷售指導建議
   - 客戶摘要 (可複製)

4. **週報 `/reports/weekly`**
   - 週期選擇
   - 各業務員表現
   - 洞察列表

### Agent H: Admin Panel (`apps/admin/`)

1. **系統設定 `/admin/settings`**
   - API 配置
   - Slack 整合設定

2. **Agent 管理 `/admin/agents`**
   - 6 個 Agent 狀態
   - Prompt 版本管理

---

## 共用組件 (`packages/ui/`)

建議優先實作：

```typescript
// 基礎組件
- Button (primary, secondary, ghost)
- Card
- Badge (status 顏色)
- Table (含排序、分頁)
- Modal
- Tabs

// 業務組件
- ScoreGauge (MEDDIC 分數儀表)
- StatusBadge (對話狀態)
- TranscriptViewer (逐字稿顯示)
- MEDDICCard (MEDDIC 六要素卡片)
- CoachingPanel (銷售建議面板)
```

---

## 開始開發

### 1. 安裝依賴

```bash
cd dashboard
bun install
```

### 2. 生成 API Client

等 API Gateway 的 `openapi.json` 產出後：

```bash
cd packages/api-client
bun run generate  # 從 openapi.json 生成類型
```

### 3. 啟動開發伺服器

```bash
cd dashboard
bun run dev  # 啟動所有 apps
```

### 4. 開發流程

1. 先完成 `packages/ui/` 的基礎組件
2. 在 `apps/web/` 實作 Dashboard 頁面
3. 使用 mock data 開發，等 API 完成再對接

---

## 重要檔案參考

- API Schema: `api-gateway/schemas/`
- API Routes: `api-gateway/routers/`
- Core Types: `core/schemas/`
- 整合計劃: `docs/BETTER-T-STACK-INTEGRATION-PLAN.md`

---

## 聯繫

如有問題，請參考：
- `docs/BETTER-T-STACK-INTEGRATION-PLAN.md` - 完整整合計劃
- `api-gateway/main.py` - API 入口
- `.claude/plans/streamed-churning-koala.md` - 開發計劃
