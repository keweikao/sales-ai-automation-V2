# Sales AI Automation V3 開發指南

## 目錄
1. [專案概覽](#專案概覽)
2. [V3 技術棧](#v3-技術棧)
3. [從 V2 保留的內容](#從-v2-保留的內容)
4. [開發階段規劃](#開發階段規劃)
5. [Phase 1: 基礎建設](#phase-1-基礎建設)
6. [Phase 2: 核心功能](#phase-2-核心功能)
7. [Phase 3: 整合測試](#phase-3-整合測試)
8. [Phase 4: 資料遷移](#phase-4-資料遷移)
9. [Phase 5: 部署上線](#phase-5-部署上線)

---

## 專案概覽

### V2 → V3 遷移目標
- **開發效率**：TypeScript 全端類型安全，減少 runtime 錯誤
- **部署速度**：Cloudflare Workers 邊緣部署，0ms 冷啟動
- **維護成本**：統一技術棧，減少 Python + TypeScript 雙語言維護

### V3 專案建立指令
```bash
bun create better-t-stack@latest Sales_ai_automation_v3 \
  --frontend tanstack-router \
  --backend hono \
  --runtime workers \
  --api orpc \
  --auth better-auth \
  --database postgres \
  --orm drizzle \
  --db-setup neon \
  --package-manager bun \
  --git \
  --web-deploy cloudflare \
  --server-deploy cloudflare \
  --addons biome turborepo ultracite
```

---

## V3 技術棧

| 層級 | 技術 | 說明 |
|------|------|------|
| Frontend | TanStack Router + React | 類型安全路由 |
| UI | shadcn/ui + Tailwind | 現代化元件庫 |
| API | oRPC | 端對端類型安全，原生 OpenAPI |
| Backend | Hono | 輕量高效，支援 Workers |
| Database | PostgreSQL (Neon) | Serverless，自動擴展 |
| ORM | Drizzle | TypeScript-first |
| Auth | Better-Auth | 內建 OAuth、Session |
| Deploy | Cloudflare Workers/Pages | 邊緣部署 |

---

## 從 V2 保留的內容

### 1. MEDDIC Agent Prompts

這些 prompt 需要複製到 V3 的 `shared/prompts/meddic/` 目錄：

#### agent1-context.md (對話情境分析)
```markdown
你是一位資深的 B2B 業務顧問，專門協助分析銷售對話。

你的任務是：
1. 閱讀對話記錄
2. 識別關鍵資訊：
   - 客戶公司背景
   - 與會人員角色
   - 討論的主題和痛點
   - 時間軸和緊迫性
3. 輸出結構化的情境摘要

輸出格式：
- company_context: 公司背景描述
- attendees: 與會者列表及角色
- main_topics: 主要討論主題
- timeline: 相關時程
```

#### agent2-buyer.md (買方分析)
```markdown
你是一位專精於 MEDDIC 銷售方法論的分析師。

根據對話內容，分析以下買方相關維度：

1. **Metrics (指標)**
   - 客戶想達成什麼可量化目標？
   - ROI 期望是什麼？

2. **Economic Buyer (經濟決策者)**
   - 誰有預算決定權？
   - 決策者的優先考量是什麼？

3. **Identify Pain (識別痛點)**
   - 客戶面臨的核心問題是什麼？
   - 痛點的影響程度如何？

輸出 JSON 格式，每個維度包含：
- score: 1-5 分
- evidence: 對話中的證據
- gaps: 缺失的資訊
```

#### agent3-seller.md (賣方分析)
```markdown
你是一位銷售教練，專門分析銷售人員的表現。

根據對話內容，分析以下賣方相關維度：

1. **Decision Criteria (決策標準)**
   - 銷售是否了解客戶的評估標準？
   - 是否有機會影響標準？

2. **Decision Process (決策流程)**
   - 銷售是否掌握採購流程？
   - 是否知道各階段的關鍵人物？

3. **Champion (內部支持者)**
   - 是否識別出支持者？
   - 支持者的影響力如何？

輸出 JSON 格式，每個維度包含：
- score: 1-5 分
- evidence: 對話中的證據
- recommendations: 改進建議
```

#### agent4-summary.md (綜合摘要)
```markdown
你是一位資深銷售主管，負責審核銷售機會。

根據前面各 Agent 的分析結果，產出：

1. **整體評分** (1-100)
2. **機會狀態**：Strong / Medium / Weak / At Risk
3. **關鍵發現**：3-5 個最重要的洞察
4. **下一步行動**：具體可執行的 3 個步驟
5. **風險提醒**：需要注意的潛在問題

輸出格式：
{
  "overall_score": number,
  "status": string,
  "key_findings": string[],
  "next_steps": string[],
  "risks": string[]
}
```

#### agent6-crm-extractor.md (CRM 資料萃取)
```markdown
你是一位 CRM 資料專家，負責從對話中萃取結構化資料。

從對話中萃取以下欄位：

**聯絡人資訊**
- name: 姓名
- title: 職稱
- email: 電子郵件
- phone: 電話

**公司資訊**
- company_name: 公司名稱
- industry: 產業
- company_size: 公司規模
- location: 地點

**機會資訊**
- deal_size: 預估金額
- timeline: 預計時程
- competition: 競爭對手
- next_meeting: 下次會議時間

輸出標準 JSON 格式，未知欄位填 null。
```

---

### 2. 資料模型定義

#### Lead (潛在客戶)
```typescript
// packages/db/src/schema/lead.ts
import { pgTable, text, timestamp, integer, jsonb } from 'drizzle-orm/pg-core';

export const leads = pgTable('leads', {
  id: text('id').primaryKey(),

  // 基本資訊
  companyName: text('company_name').notNull(),
  contactName: text('contact_name'),
  contactEmail: text('contact_email'),
  contactPhone: text('contact_phone'),
  contactTitle: text('contact_title'),

  // 分類
  source: text('source').notNull(), // manual, website, referral, conference, cold_outreach, inbound_call, slack
  status: text('status').notNull().default('new'), // new, contacted, qualified, proposal, negotiation, won, lost

  // 商機資訊
  industry: text('industry'),
  companySize: text('company_size'),
  estimatedValue: integer('estimated_value'),
  probability: integer('probability'),

  // 評分
  leadScore: integer('lead_score'),
  meddicScore: jsonb('meddic_score'), // { metrics: 3, economicBuyer: 4, ... }

  // 時間戳
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
  lastContactedAt: timestamp('last_contacted_at'),
  expectedCloseDate: timestamp('expected_close_date'),

  // 關聯
  assignedTo: text('assigned_to'),
  createdBy: text('created_by'),
});

export type Lead = typeof leads.$inferSelect;
export type NewLead = typeof leads.$inferInsert;
```

#### Conversation (對話記錄)
```typescript
// packages/db/src/schema/conversation.ts
import { pgTable, text, timestamp, integer, jsonb } from 'drizzle-orm/pg-core';

export const conversations = pgTable('conversations', {
  id: text('id').primaryKey(),
  leadId: text('lead_id').notNull(),

  // 基本資訊
  title: text('title'),
  type: text('type').notNull(), // discovery_call, demo, follow_up, negotiation, closing, support
  status: text('status').notNull().default('pending'), // pending, transcribing, analyzing, completed, failed

  // 內容
  audioUrl: text('audio_url'),
  transcript: text('transcript'),
  summary: text('summary'),

  // 分析結果
  meddicAnalysis: jsonb('meddic_analysis'),
  extractedData: jsonb('extracted_data'), // CRM 萃取結果
  sentiment: text('sentiment'), // positive, neutral, negative

  // 時間
  duration: integer('duration'), // 秒數
  conversationDate: timestamp('conversation_date'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  analyzedAt: timestamp('analyzed_at'),

  // 關聯
  participants: jsonb('participants'), // [{ name, role, company }]
  createdBy: text('created_by'),
});

export type Conversation = typeof conversations.$inferSelect;
export type NewConversation = typeof conversations.$inferInsert;
```

#### MEDDIC Analysis (分析結果)
```typescript
// packages/db/src/schema/meddic.ts
import { pgTable, text, timestamp, integer, jsonb } from 'drizzle-orm/pg-core';

export const meddicAnalyses = pgTable('meddic_analyses', {
  id: text('id').primaryKey(),
  conversationId: text('conversation_id').notNull(),
  leadId: text('lead_id').notNull(),

  // 六個維度評分 (1-5)
  metricsScore: integer('metrics_score'),
  economicBuyerScore: integer('economic_buyer_score'),
  decisionCriteriaScore: integer('decision_criteria_score'),
  decisionProcessScore: integer('decision_process_score'),
  identifyPainScore: integer('identify_pain_score'),
  championScore: integer('champion_score'),

  // 整體評分
  overallScore: integer('overall_score'), // 1-100
  status: text('status'), // Strong, Medium, Weak, At Risk

  // 詳細分析
  dimensions: jsonb('dimensions'), // 每個維度的 evidence, gaps, recommendations
  keyFindings: jsonb('key_findings'),
  nextSteps: jsonb('next_steps'),
  risks: jsonb('risks'),

  // 原始 Agent 輸出
  agentOutputs: jsonb('agent_outputs'), // { agent1: {...}, agent2: {...}, ... }

  createdAt: timestamp('created_at').defaultNow().notNull(),
});

export type MeddicAnalysis = typeof meddicAnalyses.$inferSelect;
```

---

### 3. 業務規則

#### MEDDIC 評分權重
```typescript
// packages/shared/src/constants/meddic.ts
export const MEDDIC_WEIGHTS = {
  metrics: 0.20,           // 20%
  economicBuyer: 0.20,     // 20%
  decisionCriteria: 0.15,  // 15%
  decisionProcess: 0.15,   // 15%
  identifyPain: 0.15,      // 15%
  champion: 0.15,          // 15%
} as const;

export const MEDDIC_STATUS_THRESHOLDS = {
  strong: 80,    // >= 80: Strong
  medium: 60,    // >= 60: Medium
  weak: 40,      // >= 40: Weak
  atRisk: 0,     // < 40: At Risk
} as const;

export function calculateOverallScore(scores: Record<string, number>): number {
  let total = 0;
  for (const [key, weight] of Object.entries(MEDDIC_WEIGHTS)) {
    const score = scores[key] || 0;
    total += (score / 5) * 100 * weight; // 轉換為百分比
  }
  return Math.round(total);
}

export function getStatus(overallScore: number): string {
  if (overallScore >= MEDDIC_STATUS_THRESHOLDS.strong) return 'Strong';
  if (overallScore >= MEDDIC_STATUS_THRESHOLDS.medium) return 'Medium';
  if (overallScore >= MEDDIC_STATUS_THRESHOLDS.weak) return 'Weak';
  return 'At Risk';
}
```

#### Lead 狀態流轉
```typescript
// packages/shared/src/constants/lead.ts
export const LEAD_STATUS_FLOW = {
  new: ['contacted', 'lost'],
  contacted: ['qualified', 'lost'],
  qualified: ['proposal', 'lost'],
  proposal: ['negotiation', 'lost'],
  negotiation: ['won', 'lost'],
  won: [],
  lost: ['new'], // 可以重新開啟
} as const;

export function canTransition(from: string, to: string): boolean {
  const allowed = LEAD_STATUS_FLOW[from as keyof typeof LEAD_STATUS_FLOW];
  return allowed?.includes(to as never) ?? false;
}
```

---

## 開發階段規劃

### 依賴關係圖

```
Phase 1 (並行)
├── Agent A: Database Schema
├── Agent B: UI Components
└── Agent C: External Services (LLM, Transcription)
         │
         ▼
Phase 2 (並行，依賴 Phase 1)
├── Agent D: API Routes (依賴 A, C)
├── Agent E: Frontend Pages (依賴 B, D)
└── Agent F: Slack Bot (依賴 C, D)
         │
         ▼
Phase 3
└── Agent G: Integration Testing
         │
         ▼
Phase 4
└── Agent H: Data Migration (Firestore → PostgreSQL)
         │
         ▼
Phase 5
└── Agent I: Deployment
```

---

## Phase 1: 基礎建設

### Agent A: Database Schema

**目標**：建立 Drizzle ORM schema

**檔案結構**：
```
packages/db/src/schema/
├── index.ts        # 匯出所有 schema
├── auth.ts         # Better-Auth 內建 (已存在)
├── lead.ts         # 潛在客戶
├── conversation.ts # 對話記錄
├── meddic.ts       # MEDDIC 分析
└── user.ts         # 使用者擴展欄位
```

**執行步驟**：
1. 建立上述 schema 檔案
2. 執行 `bun run db:generate` 產生 migration
3. 執行 `bun run db:push` 推送到 Neon

---

### Agent B: UI Components

**目標**：建立可重用的 UI 元件

**檔案結構**：
```
apps/web/src/components/
├── ui/              # shadcn/ui 基礎元件 (已存在)
├── lead/
│   ├── lead-table.tsx
│   ├── lead-card.tsx
│   ├── lead-form.tsx
│   └── lead-status-badge.tsx
├── conversation/
│   ├── conversation-list.tsx
│   ├── conversation-player.tsx
│   └── transcript-viewer.tsx
├── meddic/
│   ├── meddic-radar-chart.tsx
│   ├── meddic-score-card.tsx
│   └── meddic-dimension-detail.tsx
└── common/
    ├── data-table.tsx
    ├── file-upload.tsx
    └── audio-recorder.tsx
```

**執行步驟**：
1. 安裝額外套件：`bun add recharts @tanstack/react-table`
2. 建立 Lead 相關元件
3. 建立 Conversation 相關元件
4. 建立 MEDDIC 視覺化元件

---

### Agent C: External Services

**目標**：封裝外部服務 SDK

**檔案結構**：
```
packages/services/
├── package.json
├── src/
│   ├── index.ts
│   ├── llm/
│   │   ├── gemini.ts      # Google Gemini 2.0
│   │   ├── types.ts
│   │   └── prompts.ts     # 載入 shared prompts
│   ├── transcription/
│   │   ├── deepgram.ts    # 或 Google Speech-to-Text
│   │   └── types.ts
│   └── storage/
│       ├── r2.ts          # Cloudflare R2
│       └── types.ts
```

**Gemini 整合範例**：
```typescript
// packages/services/src/llm/gemini.ts
import { GoogleGenerativeAI } from '@google/generative-ai';

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);

export async function analyzeWithMeddic(
  transcript: string,
  prompt: string
): Promise<string> {
  const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' });

  const result = await model.generateContent([
    { text: prompt },
    { text: `對話記錄：\n${transcript}` },
  ]);

  return result.response.text();
}

export async function runMeddicPipeline(transcript: string) {
  // 依序執行 Agent 1-4, 6
  const context = await analyzeWithMeddic(transcript, AGENT1_PROMPT);
  const buyerAnalysis = await analyzeWithMeddic(transcript, AGENT2_PROMPT);
  const sellerAnalysis = await analyzeWithMeddic(transcript, AGENT3_PROMPT);
  const summary = await analyzeWithMeddic(
    `${context}\n${buyerAnalysis}\n${sellerAnalysis}`,
    AGENT4_PROMPT
  );
  const crmData = await analyzeWithMeddic(transcript, AGENT6_PROMPT);

  return { context, buyerAnalysis, sellerAnalysis, summary, crmData };
}
```

---

## Phase 2: 核心功能

### Agent D: API Routes

**目標**：建立 oRPC API

**檔案結構**：
```
packages/api/src/routers/
├── index.ts         # 主路由
├── lead.ts          # Lead CRUD
├── conversation.ts  # Conversation CRUD
├── meddic.ts        # MEDDIC 分析
├── upload.ts        # 檔案上傳
└── analytics.ts     # 報表分析
```

**Lead Router 範例**：
```typescript
// packages/api/src/routers/lead.ts
import { os } from '@orpc/server';
import { z } from 'zod';
import { db } from '@Sales_ai_automation_v3/db';
import { leads } from '@Sales_ai_automation_v3/db/schema';
import { eq } from 'drizzle-orm';

export const leadRouter = os.router({
  list: os
    .input(z.object({
      status: z.string().optional(),
      limit: z.number().default(20),
      offset: z.number().default(0),
    }))
    .query(async ({ input }) => {
      const query = db.select().from(leads);
      if (input.status) {
        query.where(eq(leads.status, input.status));
      }
      return query.limit(input.limit).offset(input.offset);
    }),

  getById: os
    .input(z.object({ id: z.string() }))
    .query(async ({ input }) => {
      const [lead] = await db
        .select()
        .from(leads)
        .where(eq(leads.id, input.id));
      return lead;
    }),

  create: os
    .input(z.object({
      companyName: z.string(),
      contactName: z.string().optional(),
      contactEmail: z.string().email().optional(),
      source: z.string(),
    }))
    .mutation(async ({ input }) => {
      const id = crypto.randomUUID();
      await db.insert(leads).values({ id, ...input });
      return { id };
    }),

  updateStatus: os
    .input(z.object({
      id: z.string(),
      status: z.string(),
    }))
    .mutation(async ({ input }) => {
      await db
        .update(leads)
        .set({ status: input.status, updatedAt: new Date() })
        .where(eq(leads.id, input.id));
      return { success: true };
    }),
});
```

---

### Agent E: Frontend Pages

**目標**：建立前端頁面

**檔案結構**：
```
apps/web/src/routes/
├── __root.tsx       # 根 layout (已存在)
├── index.tsx        # 首頁 Dashboard
├── login.tsx        # 登入頁 (已存在)
├── leads/
│   ├── index.tsx    # Lead 列表
│   └── $id.tsx      # Lead 詳情
├── conversations/
│   ├── index.tsx    # 對話列表
│   ├── $id.tsx      # 對話詳情
│   └── new.tsx      # 新增對話
└── analytics/
    └── index.tsx    # 分析報表
```

**Lead 列表頁範例**：
```typescript
// apps/web/src/routes/leads/index.tsx
import { createFileRoute } from '@tanstack/react-router';
import { orpc } from '../../utils/orpc';
import { LeadTable } from '../../components/lead/lead-table';

export const Route = createFileRoute('/leads/')({
  component: LeadsPage,
  loader: async () => {
    return orpc.lead.list.query({ limit: 50 });
  },
});

function LeadsPage() {
  const leads = Route.useLoaderData();

  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">潛在客戶</h1>
        <Link to="/leads/new">
          <Button>新增客戶</Button>
        </Link>
      </div>
      <LeadTable data={leads} />
    </div>
  );
}
```

---

### Agent F: Slack Bot

**目標**：Slack 整合

**檔案結構**：
```
apps/slack-bot/
├── package.json
├── src/
│   ├── index.ts         # 入口
│   ├── app.ts           # Bolt app 設定
│   ├── commands/
│   │   ├── analyze.ts   # /analyze 指令
│   │   ├── lead.ts      # /lead 指令
│   │   └── report.ts    # /report 指令
│   ├── events/
│   │   ├── message.ts   # 訊息事件
│   │   └── file.ts      # 檔案上傳事件
│   └── blocks/
│       ├── meddic-summary.ts
│       └── lead-card.ts
```

**Slack App 範例**：
```typescript
// apps/slack-bot/src/app.ts
import { App } from '@slack/bolt';

export const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET,
});

// /analyze 指令：分析對話
app.command('/analyze', async ({ command, ack, respond }) => {
  await ack();

  // 取得附件的音檔
  // 呼叫轉錄服務
  // 呼叫 MEDDIC 分析
  // 回傳結果

  await respond({
    blocks: buildMeddicSummaryBlocks(analysis),
  });
});

// 檔案上傳事件
app.event('file_shared', async ({ event, client }) => {
  const file = await client.files.info({ file: event.file_id });

  if (file.file?.mimetype?.startsWith('audio/')) {
    // 自動分析音檔
  }
});
```

---

## Phase 3: 整合測試

### Agent G: Integration

**測試清單**：
- [ ] 使用者登入流程
- [ ] Lead CRUD 完整流程
- [ ] 音檔上傳 → 轉錄 → MEDDIC 分析
- [ ] Slack 指令回應
- [ ] 資料一致性

**測試指令**：
```bash
bun run test
bun run test:e2e
```

---

## Phase 4: 資料遷移

### Agent H: Migration Script

**從 Firestore 遷移到 PostgreSQL**：

```typescript
// scripts/migrate-firestore-to-postgres.ts
import { initializeApp, cert } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { db } from '@Sales_ai_automation_v3/db';
import { leads, conversations, meddicAnalyses } from '@Sales_ai_automation_v3/db/schema';

// 初始化 Firebase
initializeApp({
  credential: cert('./service-account.json'),
});
const firestore = getFirestore();

async function migrateLeads() {
  const snapshot = await firestore.collection('leads').get();

  for (const doc of snapshot.docs) {
    const data = doc.data();
    await db.insert(leads).values({
      id: doc.id,
      companyName: data.company_name,
      contactName: data.contact_name,
      contactEmail: data.contact_email,
      source: data.source,
      status: data.status,
      createdAt: data.created_at?.toDate(),
      // ... 其他欄位對應
    });
  }

  console.log(`Migrated ${snapshot.size} leads`);
}

async function migrateConversations() {
  // 類似邏輯
}

async function main() {
  await migrateLeads();
  await migrateConversations();
  console.log('Migration complete!');
}

main();
```

---

## Phase 5: 部署上線

### Agent I: Deployment

**環境變數設定** (.env)：
```env
# Database
DATABASE_URL="postgresql://..."

# Auth
BETTER_AUTH_SECRET="your-secret-key"
BETTER_AUTH_URL="https://your-app.pages.dev"

# Google
GOOGLE_CLIENT_ID="..."
GOOGLE_CLIENT_SECRET="..."
GEMINI_API_KEY="..."

# Transcription
DEEPGRAM_API_KEY="..."

# Slack
SLACK_BOT_TOKEN="xoxb-..."
SLACK_SIGNING_SECRET="..."

# Storage
CLOUDFLARE_R2_ACCESS_KEY="..."
CLOUDFLARE_R2_SECRET_KEY="..."
CLOUDFLARE_R2_BUCKET="..."
```

**部署指令**：
```bash
# 前端 (Cloudflare Pages)
bun run build
npx wrangler pages deploy apps/web/dist

# 後端 (Cloudflare Workers)
cd apps/server
npx wrangler deploy
```

**Wrangler 設定** (apps/server/wrangler.toml)：
```toml
name = "sales-ai-v3-api"
main = "dist/index.js"
compatibility_date = "2024-01-01"

[vars]
ENVIRONMENT = "production"

[[d1_databases]]
binding = "DB"
database_name = "sales-ai-v3"
database_id = "your-database-id"
```

---

## 快速參考

### 常用指令

```bash
# 開發
bun run dev           # 啟動所有服務
bun run dev:web       # 只啟動前端
bun run dev:server    # 只啟動後端

# 資料庫
bun run db:generate   # 產生 migration
bun run db:push       # 推送 schema
bun run db:studio     # 開啟 Drizzle Studio

# 建置
bun run build         # 建置所有
bun run check-types   # 類型檢查

# 測試
bun run test          # 執行測試
bun run lint          # 程式碼檢查
```

### API 端點

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | /api/leads | 取得 Lead 列表 |
| POST | /api/leads | 建立 Lead |
| GET | /api/leads/:id | 取得單一 Lead |
| PUT | /api/leads/:id | 更新 Lead |
| GET | /api/conversations | 取得對話列表 |
| POST | /api/conversations | 建立對話 |
| POST | /api/conversations/:id/analyze | 執行 MEDDIC 分析 |
| GET | /api/analytics/dashboard | 取得儀表板資料 |

---

## 備註

- 這份文件包含了 V2 的核心業務邏輯和 V3 的完整開發規劃
- 可以按照 Phase 順序逐步實作
- Phase 1 的三個 Agent 可以並行開發
- 有任何問題可以參考對應的 Agent 章節
