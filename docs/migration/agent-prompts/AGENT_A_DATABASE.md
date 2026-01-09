# Agent A: Database Schema

## 任務說明

你是 Database Schema Agent，負責在 Sales_ai_automation_v3 專案中建立 Drizzle ORM schema。

## 前置條件

- 專案 `/home/user/Sales_ai_automation_v3` 已建立
- `bun install` 已執行

## 任務清單

### 1. 閱讀舊專案資料結構

讀取以下檔案了解現有資料模型：

```
/home/user/sales-ai-automation-V2/core/schemas/lead.py
/home/user/sales-ai-automation-V2/core/schemas/conversation.py
/home/user/sales-ai-automation-V2/api-gateway/schemas/conversation.py
/home/user/sales-ai-automation-V2/api-gateway/schemas/analytics.py
/home/user/sales-ai-automation-V2/core/database/repositories/conversation_repository.py
/home/user/sales-ai-automation-V2/core/database/repositories/lead_repository.py
```

### 2. 建立 Drizzle Schema

在 `/home/user/Sales_ai_automation_v3/packages/db/src/schema/` 建立以下檔案：

#### leads.ts
```typescript
import { pgTable, varchar, integer, timestamp, pgEnum, text } from 'drizzle-orm/pg-core'

export const leadSourceEnum = pgEnum('lead_source', [
  'squarespace', 'linkedin', 'referral', 'website', 'event', 'cold_outreach', 'other'
])

export const leadStatusEnum = pgEnum('lead_status', [
  'new', 'contacted', 'mql', 'sql', 'opportunity', 'negotiation', 'closed_won', 'closed_lost'
])

export const leads = pgTable('leads', {
  id: varchar('id', { length: 255 }).primaryKey(),
  email: varchar('email', { length: 255 }).notNull(),
  name: varchar('name', { length: 255 }),
  company: varchar('company', { length: 255 }),
  phone: varchar('phone', { length: 50 }),
  title: varchar('title', { length: 255 }),
  source: leadSourceEnum('source').default('other'),
  status: leadStatusEnum('status').default('new'),
  score: integer('score').default(0),
  salesforceId: varchar('salesforce_id', { length: 255 }),
  tags: text('tags'), // JSON array as string
  utmSource: varchar('utm_source', { length: 255 }),
  utmMedium: varchar('utm_medium', { length: 255 }),
  utmCampaign: varchar('utm_campaign', { length: 255 }),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
  firstContactAt: timestamp('first_contact_at'),
})

export type Lead = typeof leads.$inferSelect
export type NewLead = typeof leads.$inferInsert
```

#### conversations.ts
```typescript
import { pgTable, varchar, integer, timestamp, text, jsonb, pgEnum, real } from 'drizzle-orm/pg-core'
import { leads } from './leads'

export const conversationStatusEnum = pgEnum('conversation_status', [
  'pending', 'transcribing', 'analyzing', 'completed', 'failed'
])

export const conversations = pgTable('conversations', {
  id: varchar('id', { length: 255 }).primaryKey(),
  leadId: varchar('lead_id', { length: 255 }).references(() => leads.id),
  salesRepId: varchar('sales_rep_id', { length: 255 }),
  salesRepName: varchar('sales_rep_name', { length: 255 }),
  status: conversationStatusEnum('status').default('pending'),
  conversationType: varchar('conversation_type', { length: 50 }),

  // Transcript
  transcriptFullText: text('transcript_full_text'),
  transcriptSegments: jsonb('transcript_segments'),
  transcriptLanguage: varchar('transcript_language', { length: 10 }).default('zh-TW'),
  audioDurationSeconds: real('audio_duration_seconds'),
  audioFileUri: varchar('audio_file_uri', { length: 500 }),

  // Analysis
  meddicScore: integer('meddic_score'),
  progressScore: integer('progress_score'),
  qualificationStatus: varchar('qualification_status', { length: 50 }),
  summary: text('summary'),
  customerSummary: text('customer_summary'),
  analysisRaw: jsonb('analysis_raw'),

  // Timestamps
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
  completedAt: timestamp('completed_at'),
  analyzedAt: timestamp('analyzed_at'),
})

export type Conversation = typeof conversations.$inferSelect
export type NewConversation = typeof conversations.$inferInsert
```

#### sales-reps.ts
```typescript
import { pgTable, varchar, timestamp } from 'drizzle-orm/pg-core'

export const salesReps = pgTable('sales_reps', {
  id: varchar('id', { length: 255 }).primaryKey(),
  name: varchar('name', { length: 255 }).notNull(),
  email: varchar('email', { length: 255 }),
  slackUserId: varchar('slack_user_id', { length: 50 }),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
})

export type SalesRep = typeof salesReps.$inferSelect
export type NewSalesRep = typeof salesReps.$inferInsert
```

#### analytics.ts
```typescript
import { pgTable, varchar, integer, timestamp, real, date } from 'drizzle-orm/pg-core'

export const dailyStats = pgTable('daily_stats', {
  id: varchar('id', { length: 20 }).primaryKey(), // format: YYYY-MM-DD
  date: date('date').notNull(),
  totalConversations: integer('total_conversations').default(0),
  completedConversations: integer('completed_conversations').default(0),
  avgMeddicScore: real('avg_meddic_score'),
  avgProgressScore: real('avg_progress_score'),
  createdAt: timestamp('created_at').defaultNow(),
})

export type DailyStat = typeof dailyStats.$inferSelect
export type NewDailyStat = typeof dailyStats.$inferInsert
```

#### index.ts
```typescript
export * from './leads'
export * from './conversations'
export * from './sales-reps'
export * from './analytics'
```

### 3. 執行 Migration

```bash
cd /home/user/Sales_ai_automation_v3
bun run db:generate
bun run db:push
```

### 4. 建立完成報告

建立 `/home/user/Sales_ai_automation_v3/packages/db/AGENT_A_COMPLETE.md`：

```markdown
# Agent A 完成報告

## 建立的 Tables

| Table | 說明 | 欄位數 |
|-------|------|--------|
| leads | 潛客資料 | 16 |
| conversations | 對話記錄 | 18 |
| sales_reps | 業務員 | 5 |
| daily_stats | 每日統計 | 7 |

## Enums

- lead_source: 7 values
- lead_status: 8 values
- conversation_status: 5 values

## 關聯

- conversations.leadId -> leads.id

## Migration 結果

- [x] Schema 生成成功
- [x] Database push 成功
- [x] 類型導出正確

## 注意事項

（記錄任何問題或特殊處理）
```

## 完成標準

- [ ] 所有 schema 檔案建立
- [ ] index.ts 正確導出
- [ ] Migration 執行成功
- [ ] 完成報告建立
