# Agent D: API Routers

## 任務說明

你是 API Routers Agent，負責建立 oRPC API 端點。

## 前置條件

**必須等待 Agent A 完成**

檢查：`/home/user/Sales_ai_automation_v3/packages/db/AGENT_A_COMPLETE.md` 存在

## 任務清單

### 1. 閱讀舊專案 API

```
/home/user/sales-ai-automation-V2/api-gateway/routers/conversations.py
/home/user/sales-ai-automation-V2/api-gateway/routers/leads.py
/home/user/sales-ai-automation-V2/api-gateway/routers/analytics.py
/home/user/sales-ai-automation-V2/api-gateway/routers/health.py
```

### 2. 建立 Health Router

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/routers/health.ts
import { os } from '@orpc/server'

export const healthRouter = os.router({
  check: os.handler(async () => {
    return {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      version: '3.0.0',
    }
  }),
})
```

### 3. 建立 Conversations Router

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/routers/conversations.ts
import { os } from '@orpc/server'
import { z } from 'zod'
import { db } from '@sales-ai/db'
import { conversations, type Conversation } from '@sales-ai/db/schema'
import { eq, desc, and, gte, lte, sql } from 'drizzle-orm'

export const conversationsRouter = os.router({
  list: os
    .input(
      z.object({
        status: z.string().optional(),
        salesRepId: z.string().optional(),
        startDate: z.string().datetime().optional(),
        endDate: z.string().datetime().optional(),
        limit: z.number().min(1).max(100).default(50),
        offset: z.number().min(0).default(0),
      })
    )
    .handler(async ({ input }) => {
      const conditions = []

      if (input.status) {
        conditions.push(eq(conversations.status, input.status as any))
      }
      if (input.salesRepId) {
        conditions.push(eq(conversations.salesRepId, input.salesRepId))
      }
      if (input.startDate) {
        conditions.push(gte(conversations.createdAt, new Date(input.startDate)))
      }
      if (input.endDate) {
        conditions.push(lte(conversations.createdAt, new Date(input.endDate)))
      }

      const items = await db
        .select()
        .from(conversations)
        .where(conditions.length > 0 ? and(...conditions) : undefined)
        .orderBy(desc(conversations.createdAt))
        .limit(input.limit)
        .offset(input.offset)

      const [countResult] = await db
        .select({ count: sql<number>`count(*)` })
        .from(conversations)
        .where(conditions.length > 0 ? and(...conditions) : undefined)

      return {
        items,
        total: countResult.count,
        limit: input.limit,
        offset: input.offset,
      }
    }),

  getById: os
    .input(z.object({ id: z.string() }))
    .handler(async ({ input }) => {
      const [conversation] = await db
        .select()
        .from(conversations)
        .where(eq(conversations.id, input.id))

      if (!conversation) {
        throw new Error(`Conversation not found: ${input.id}`)
      }

      return conversation
    }),

  getAnalysis: os
    .input(z.object({ id: z.string() }))
    .handler(async ({ input }) => {
      const [conversation] = await db
        .select({
          id: conversations.id,
          meddicScore: conversations.meddicScore,
          progressScore: conversations.progressScore,
          qualificationStatus: conversations.qualificationStatus,
          summary: conversations.summary,
          customerSummary: conversations.customerSummary,
          analysisRaw: conversations.analysisRaw,
          analyzedAt: conversations.analyzedAt,
        })
        .from(conversations)
        .where(eq(conversations.id, input.id))

      if (!conversation) {
        throw new Error(`Conversation not found: ${input.id}`)
      }

      return conversation
    }),

  create: os
    .input(
      z.object({
        id: z.string().optional(),
        leadId: z.string().optional(),
        salesRepId: z.string().optional(),
        salesRepName: z.string().optional(),
        conversationType: z.string().optional(),
        audioFileUri: z.string().optional(),
      })
    )
    .handler(async ({ input }) => {
      const id = input.id ?? `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

      const [conversation] = await db
        .insert(conversations)
        .values({
          id,
          leadId: input.leadId,
          salesRepId: input.salesRepId,
          salesRepName: input.salesRepName,
          conversationType: input.conversationType,
          audioFileUri: input.audioFileUri,
          status: 'pending',
        })
        .returning()

      return conversation
    }),

  updateStatus: os
    .input(
      z.object({
        id: z.string(),
        status: z.enum(['pending', 'transcribing', 'analyzing', 'completed', 'failed']),
      })
    )
    .handler(async ({ input }) => {
      const updateData: any = {
        status: input.status,
        updatedAt: new Date(),
      }

      if (input.status === 'completed') {
        updateData.completedAt = new Date()
      }

      const [updated] = await db
        .update(conversations)
        .set(updateData)
        .where(eq(conversations.id, input.id))
        .returning()

      return updated
    }),

  saveAnalysis: os
    .input(
      z.object({
        id: z.string(),
        meddicScore: z.number().optional(),
        progressScore: z.number().optional(),
        qualificationStatus: z.string().optional(),
        summary: z.string().optional(),
        customerSummary: z.string().optional(),
        analysisRaw: z.any().optional(),
      })
    )
    .handler(async ({ input }) => {
      const [updated] = await db
        .update(conversations)
        .set({
          meddicScore: input.meddicScore,
          progressScore: input.progressScore,
          qualificationStatus: input.qualificationStatus,
          summary: input.summary,
          customerSummary: input.customerSummary,
          analysisRaw: input.analysisRaw,
          analyzedAt: new Date(),
          updatedAt: new Date(),
        })
        .where(eq(conversations.id, input.id))
        .returning()

      return updated
    }),
})
```

### 4. 建立 Leads Router

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/routers/leads.ts
import { os } from '@orpc/server'
import { z } from 'zod'
import { db } from '@sales-ai/db'
import { leads } from '@sales-ai/db/schema'
import { eq, desc, sql } from 'drizzle-orm'

export const leadsRouter = os.router({
  list: os
    .input(
      z.object({
        status: z.string().optional(),
        limit: z.number().min(1).max(100).default(50),
        offset: z.number().min(0).default(0),
      })
    )
    .handler(async ({ input }) => {
      const query = db.select().from(leads)

      if (input.status) {
        query.where(eq(leads.status, input.status as any))
      }

      const items = await query
        .orderBy(desc(leads.createdAt))
        .limit(input.limit)
        .offset(input.offset)

      return { items, total: items.length, limit: input.limit, offset: input.offset }
    }),

  getById: os
    .input(z.object({ id: z.string() }))
    .handler(async ({ input }) => {
      const [lead] = await db.select().from(leads).where(eq(leads.id, input.id))

      if (!lead) {
        throw new Error(`Lead not found: ${input.id}`)
      }

      return lead
    }),

  getByEmail: os
    .input(z.object({ email: z.string().email() }))
    .handler(async ({ input }) => {
      const [lead] = await db.select().from(leads).where(eq(leads.email, input.email))
      return lead ?? null
    }),

  create: os
    .input(
      z.object({
        email: z.string().email(),
        name: z.string().optional(),
        company: z.string().optional(),
        phone: z.string().optional(),
        title: z.string().optional(),
        source: z.string().optional(),
      })
    )
    .handler(async ({ input }) => {
      const id = `lead_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

      const [lead] = await db
        .insert(leads)
        .values({
          id,
          email: input.email,
          name: input.name,
          company: input.company,
          phone: input.phone,
          title: input.title,
          source: (input.source as any) ?? 'other',
        })
        .returning()

      return lead
    }),

  updateStatus: os
    .input(
      z.object({
        id: z.string(),
        status: z.enum([
          'new', 'contacted', 'mql', 'sql', 'opportunity', 'negotiation', 'closed_won', 'closed_lost'
        ]),
      })
    )
    .handler(async ({ input }) => {
      const [updated] = await db
        .update(leads)
        .set({ status: input.status, updatedAt: new Date() })
        .where(eq(leads.id, input.id))
        .returning()

      return updated
    }),

  updateScore: os
    .input(
      z.object({
        id: z.string(),
        score: z.number().min(0).max(100),
      })
    )
    .handler(async ({ input }) => {
      const [updated] = await db
        .update(leads)
        .set({ score: input.score, updatedAt: new Date() })
        .where(eq(leads.id, input.id))
        .returning()

      return updated
    }),
})
```

### 5. 建立 Analytics Router

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/routers/analytics.ts
import { os } from '@orpc/server'
import { z } from 'zod'
import { db } from '@sales-ai/db'
import { conversations, dailyStats } from '@sales-ai/db/schema'
import { sql, gte, desc } from 'drizzle-orm'

export const analyticsRouter = os.router({
  dashboard: os.handler(async () => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    const [stats] = await db
      .select({
        totalConversations: sql<number>`count(*)`,
        completedToday: sql<number>`count(*) filter (where created_at >= ${today} and status = 'completed')`,
        pendingAnalysis: sql<number>`count(*) filter (where status in ('pending', 'transcribing', 'analyzing'))`,
        avgMeddicScore: sql<number>`coalesce(avg(meddic_score), 0)`,
      })
      .from(conversations)

    // Top performers
    const topPerformers = await db
      .select({
        id: conversations.salesRepId,
        name: conversations.salesRepName,
        conversationCount: sql<number>`count(*)`,
        avgMeddicScore: sql<number>`coalesce(avg(meddic_score), 0)`,
      })
      .from(conversations)
      .where(sql`sales_rep_id is not null`)
      .groupBy(conversations.salesRepId, conversations.salesRepName)
      .orderBy(sql`avg(meddic_score) desc nulls last`)
      .limit(5)

    return {
      totalConversations: Number(stats.totalConversations),
      completedToday: Number(stats.completedToday),
      pendingAnalysis: Number(stats.pendingAnalysis),
      avgMeddicScore: Number(stats.avgMeddicScore.toFixed(1)),
      conversionRate: 0, // TODO: Calculate from leads
      topPerformers: topPerformers.map((p) => ({
        id: p.id ?? 'unknown',
        name: p.name ?? 'Unknown',
        conversationCount: Number(p.conversationCount),
        avgMeddicScore: Number(p.avgMeddicScore.toFixed(1)),
        trend: 'stable' as const,
      })),
      recentTrend: 'stable',
      lastUpdated: new Date().toISOString(),
    }
  }),

  trends: os
    .input(
      z.object({
        period: z.enum(['7d', '30d', '90d']).default('7d'),
      })
    )
    .handler(async ({ input }) => {
      const days = input.period === '7d' ? 7 : input.period === '30d' ? 30 : 90
      const startDate = new Date()
      startDate.setDate(startDate.getDate() - days)

      const data = await db
        .select()
        .from(dailyStats)
        .where(gte(dailyStats.date, startDate.toISOString().split('T')[0]))
        .orderBy(dailyStats.date)

      return {
        period: input.period,
        data: data.map((d) => ({
          date: d.date,
          conversationCount: d.totalConversations ?? 0,
          avgMeddicScore: d.avgMeddicScore ?? 0,
        })),
        overallTrend: 'stable',
      }
    }),

  repStats: os
    .input(z.object({ repId: z.string() }))
    .handler(async ({ input }) => {
      const [stats] = await db
        .select({
          conversationCount: sql<number>`count(*)`,
          avgMeddicScore: sql<number>`coalesce(avg(meddic_score), 0)`,
          name: conversations.salesRepName,
        })
        .from(conversations)
        .where(sql`sales_rep_id = ${input.repId}`)
        .groupBy(conversations.salesRepName)

      if (!stats) {
        throw new Error(`Sales rep not found: ${input.repId}`)
      }

      return {
        id: input.repId,
        name: stats.name ?? 'Unknown',
        conversationCount: Number(stats.conversationCount),
        avgMeddicScore: Number(stats.avgMeddicScore.toFixed(1)),
        trend: 'stable',
      }
    }),
})
```

### 6. 建立主 Router

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/routers/index.ts
import { os } from '@orpc/server'
import { healthRouter } from './health'
import { conversationsRouter } from './conversations'
import { leadsRouter } from './leads'
import { analyticsRouter } from './analytics'

export const appRouter = os.router({
  health: healthRouter,
  conversations: conversationsRouter,
  leads: leadsRouter,
  analytics: analyticsRouter,
})

export type AppRouter = typeof appRouter
```

### 7. 建立完成報告

建立 `/home/user/Sales_ai_automation_v3/apps/server/src/routers/AGENT_D_COMPLETE.md`：

```markdown
# Agent D 完成報告

## API 端點列表

### Health
- `health.check` - 健康檢查

### Conversations
- `conversations.list` - 列出對話
- `conversations.getById` - 取得單一對話
- `conversations.getAnalysis` - 取得分析結果
- `conversations.create` - 建立對話
- `conversations.updateStatus` - 更新狀態
- `conversations.saveAnalysis` - 儲存分析

### Leads
- `leads.list` - 列出潛客
- `leads.getById` - 取得單一潛客
- `leads.getByEmail` - 用 email 查詢
- `leads.create` - 建立潛客
- `leads.updateStatus` - 更新狀態
- `leads.updateScore` - 更新分數

### Analytics
- `analytics.dashboard` - 儀表板統計
- `analytics.trends` - 趨勢資料
- `analytics.repStats` - 業務員統計

## 類型導出

AppRouter 類型已導出，供前端使用。

## 注意事項

（記錄任何問題或特殊處理）
```

## 完成標準

- [ ] health.ts 建立
- [ ] conversations.ts 建立
- [ ] leads.ts 建立
- [ ] analytics.ts 建立
- [ ] index.ts 正確導出 appRouter
- [ ] AppRouter 類型導出
- [ ] 完成報告建立
