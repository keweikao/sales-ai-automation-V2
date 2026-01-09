# Agent H: Data Migration

## 任務說明

你是 Data Migration Agent，負責將資料從 Firestore 遷移到 PostgreSQL。

## 前置條件

**必須等待 Agent G 完成**

檢查：`/home/user/Sales_ai_automation_v3/AGENT_G_COMPLETE.md` 存在

## 任務清單

### 1. 安裝 Firestore 依賴

```bash
cd /home/user/Sales_ai_automation_v3
bun add @google-cloud/firestore
```

### 2. 建立主遷移腳本

```typescript
// /home/user/Sales_ai_automation_v3/scripts/migrate-data.ts
import { Firestore } from '@google-cloud/firestore'
import { db } from '../packages/db/src/client'
import { leads, conversations, salesReps } from '../packages/db/src/schema'

// Initialize Firestore with credentials from old project
const firestore = new Firestore({
  projectId: process.env.GCP_PROJECT_ID,
  keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS,
})

interface MigrationStats {
  leads: { total: number; migrated: number; errors: number }
  conversations: { total: number; migrated: number; errors: number }
  salesReps: { total: number; migrated: number; errors: number }
}

const stats: MigrationStats = {
  leads: { total: 0, migrated: 0, errors: 0 },
  conversations: { total: 0, migrated: 0, errors: 0 },
  salesReps: { total: 0, migrated: 0, errors: 0 },
}

async function migrateLeads() {
  console.log('📦 Migrating leads...')

  const snapshot = await firestore.collection('leads').get()
  stats.leads.total = snapshot.docs.length

  const batchSize = 500
  const batches = []

  for (let i = 0; i < snapshot.docs.length; i += batchSize) {
    const batch = snapshot.docs.slice(i, i + batchSize)
    batches.push(batch)
  }

  for (const batch of batches) {
    const leadsData = batch.map(doc => {
      const data = doc.data()
      return {
        id: doc.id,
        email: data.email || `unknown_${doc.id}@example.com`,
        name: data.name || null,
        company: data.company || null,
        phone: data.phone || null,
        title: data.title || null,
        source: mapLeadSource(data.source),
        status: mapLeadStatus(data.status),
        score: data.score || 0,
        salesforceId: data.salesforce_id || null,
        tags: JSON.stringify(data.tags || []),
        utmSource: data.utm?.source || null,
        utmMedium: data.utm?.medium || null,
        utmCampaign: data.utm?.campaign || null,
        createdAt: data.created_at?.toDate() || new Date(),
        updatedAt: data.updated_at?.toDate() || new Date(),
        firstContactAt: data.first_contact_at?.toDate() || null,
      }
    })

    try {
      await db.insert(leads).values(leadsData).onConflictDoNothing()
      stats.leads.migrated += leadsData.length
      console.log(`  ✓ Migrated ${stats.leads.migrated}/${stats.leads.total} leads`)
    } catch (error) {
      console.error(`  ✗ Error migrating batch:`, error)
      stats.leads.errors += leadsData.length
    }
  }
}

async function migrateConversations() {
  console.log('📦 Migrating conversations...')

  // Get from sales_cases collection
  const casesSnapshot = await firestore.collection('sales_cases').get()
  stats.conversations.total = casesSnapshot.docs.length

  for (const doc of casesSnapshot.docs) {
    try {
      const data = doc.data()

      // Get analysis from cases collection
      const analysisDoc = await firestore.collection('cases').doc(doc.id).get()
      const analysis = analysisDoc.exists ? analysisDoc.data()?.analysis : null
      const agents = analysis?.agents || {}

      // Extract analysis data
      const agent1 = agents.agent1?.data || {}
      const agent2 = agents.agent2?.data || {}
      const agent3 = agents.agent3?.data || {}
      const agent4 = agents.agent4?.data || {}

      await db.insert(conversations).values({
        id: doc.id,
        leadId: data.lead_id || null,
        salesRepId: data.sales_rep_id || null,
        salesRepName: data.sales_rep_name || null,
        status: mapConversationStatus(data.status),
        conversationType: data.conversation_type || null,

        // Transcript
        transcriptFullText: data.transcript?.full_text || null,
        transcriptSegments: data.transcript?.segments ? JSON.stringify(data.transcript.segments) : null,
        transcriptLanguage: data.transcript?.language || 'zh-TW',
        audioDurationSeconds: data.transcript?.duration_seconds || null,
        audioFileUri: data.audio_file_uri || null,

        // Analysis
        meddicScore: agent2.meddic_score || null,
        progressScore: agent3.progress_score || null,
        qualificationStatus: agent2.qualification_status || null,
        summary: agent4.executive_summary || null,
        customerSummary: agent4.customer_summary || null,
        analysisRaw: analysis ? JSON.stringify(agents) : null,

        // Timestamps
        createdAt: data.created_at?.toDate() || new Date(),
        updatedAt: data.updated_at?.toDate() || new Date(),
        completedAt: data.completed_at?.toDate() || null,
        analyzedAt: analysis ? new Date() : null,
      }).onConflictDoNothing()

      stats.conversations.migrated++

      if (stats.conversations.migrated % 50 === 0) {
        console.log(`  ✓ Migrated ${stats.conversations.migrated}/${stats.conversations.total} conversations`)
      }
    } catch (error) {
      console.error(`  ✗ Error migrating conversation ${doc.id}:`, error)
      stats.conversations.errors++
    }
  }

  console.log(`  ✓ Migrated ${stats.conversations.migrated}/${stats.conversations.total} conversations`)
}

async function migrateSalesReps() {
  console.log('📦 Extracting sales reps from conversations...')

  // Extract unique sales reps from conversations
  const snapshot = await firestore.collection('sales_cases').get()
  const repsMap = new Map<string, { name: string; slackUserId?: string }>()

  for (const doc of snapshot.docs) {
    const data = doc.data()
    if (data.sales_rep_id && data.sales_rep_name) {
      repsMap.set(data.sales_rep_id, {
        name: data.sales_rep_name,
        slackUserId: data.slack_user_id,
      })
    }
  }

  stats.salesReps.total = repsMap.size

  for (const [id, rep] of repsMap) {
    try {
      await db.insert(salesReps).values({
        id,
        name: rep.name,
        slackUserId: rep.slackUserId || null,
      }).onConflictDoNothing()

      stats.salesReps.migrated++
    } catch (error) {
      console.error(`  ✗ Error migrating sales rep ${id}:`, error)
      stats.salesReps.errors++
    }
  }

  console.log(`  ✓ Migrated ${stats.salesReps.migrated}/${stats.salesReps.total} sales reps`)
}

// Helper functions
function mapLeadSource(source: string | undefined): any {
  const validSources = ['squarespace', 'linkedin', 'referral', 'website', 'event', 'cold_outreach', 'other']
  return validSources.includes(source || '') ? source : 'other'
}

function mapLeadStatus(status: string | undefined): any {
  const validStatuses = ['new', 'contacted', 'mql', 'sql', 'opportunity', 'negotiation', 'closed_won', 'closed_lost']
  return validStatuses.includes(status || '') ? status : 'new'
}

function mapConversationStatus(status: string | undefined): any {
  const validStatuses = ['pending', 'transcribing', 'analyzing', 'completed', 'failed']
  return validStatuses.includes(status || '') ? status : 'pending'
}

async function main() {
  console.log('🚀 Starting data migration...\n')

  const startTime = Date.now()

  await migrateLeads()
  await migrateSalesReps()
  await migrateConversations()

  const duration = ((Date.now() - startTime) / 1000).toFixed(2)

  console.log('\n📊 Migration Summary:')
  console.log('─'.repeat(50))
  console.log(`Leads:         ${stats.leads.migrated}/${stats.leads.total} (${stats.leads.errors} errors)`)
  console.log(`Sales Reps:    ${stats.salesReps.migrated}/${stats.salesReps.total} (${stats.salesReps.errors} errors)`)
  console.log(`Conversations: ${stats.conversations.migrated}/${stats.conversations.total} (${stats.conversations.errors} errors)`)
  console.log('─'.repeat(50))
  console.log(`Total time: ${duration}s`)

  if (stats.leads.errors + stats.conversations.errors + stats.salesReps.errors > 0) {
    console.log('\n⚠️  Some records failed to migrate. Check the logs above.')
    process.exit(1)
  } else {
    console.log('\n✅ Migration completed successfully!')
  }
}

main().catch(console.error)
```

### 3. 建立驗證腳本

```typescript
// /home/user/Sales_ai_automation_v3/scripts/validate-migration.ts
import { Firestore } from '@google-cloud/firestore'
import { db } from '../packages/db/src/client'
import { leads, conversations, salesReps } from '../packages/db/src/schema'
import { sql } from 'drizzle-orm'

const firestore = new Firestore({
  projectId: process.env.GCP_PROJECT_ID,
  keyFilename: process.env.GOOGLE_APPLICATION_CREDENTIALS,
})

async function validateMigration() {
  console.log('🔍 Validating migration...\n')

  // Count comparisons
  const firestoreLeadsCount = (await firestore.collection('leads').count().get()).data().count
  const firestoreCasesCount = (await firestore.collection('sales_cases').count().get()).data().count

  const [pgLeadsCount] = await db.select({ count: sql<number>`count(*)` }).from(leads)
  const [pgConversationsCount] = await db.select({ count: sql<number>`count(*)` }).from(conversations)
  const [pgSalesRepsCount] = await db.select({ count: sql<number>`count(*)` }).from(salesReps)

  console.log('Record Counts:')
  console.log('─'.repeat(50))
  console.log(`Leads:         Firestore=${firestoreLeadsCount}, PostgreSQL=${pgLeadsCount.count}`)
  console.log(`Conversations: Firestore=${firestoreCasesCount}, PostgreSQL=${pgConversationsCount.count}`)
  console.log(`Sales Reps:    PostgreSQL=${pgSalesRepsCount.count} (extracted)`)
  console.log('─'.repeat(50))

  // Spot check - random samples
  console.log('\n🎲 Spot checking random records...')

  // Check a few leads
  const sampleLeads = await firestore.collection('leads').limit(3).get()
  for (const doc of sampleLeads.docs) {
    const [pgLead] = await db.select().from(leads).where(sql`id = ${doc.id}`)
    if (pgLead) {
      const fsData = doc.data()
      const match = pgLead.email === fsData.email
      console.log(`  Lead ${doc.id}: ${match ? '✓' : '✗'}`)
    } else {
      console.log(`  Lead ${doc.id}: ✗ (not found in PostgreSQL)`)
    }
  }

  // Check a few conversations
  const sampleConvs = await firestore.collection('sales_cases').limit(3).get()
  for (const doc of sampleConvs.docs) {
    const [pgConv] = await db.select().from(conversations).where(sql`id = ${doc.id}`)
    if (pgConv) {
      console.log(`  Conversation ${doc.id}: ✓`)
    } else {
      console.log(`  Conversation ${doc.id}: ✗ (not found in PostgreSQL)`)
    }
  }

  console.log('\n✅ Validation complete!')
}

validateMigration().catch(console.error)
```

### 4. 建立回滾腳本

```typescript
// /home/user/Sales_ai_automation_v3/scripts/rollback-migration.ts
import { db } from '../packages/db/src/client'
import { leads, conversations, salesReps, dailyStats } from '../packages/db/src/schema'
import { sql } from 'drizzle-orm'

async function rollback() {
  console.log('⚠️  Rolling back migration...\n')
  console.log('This will DELETE all data in PostgreSQL.')
  console.log('Firestore data will NOT be affected.\n')

  // Confirmation prompt
  const readline = await import('readline')
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  })

  const answer = await new Promise<string>((resolve) => {
    rl.question('Type "ROLLBACK" to confirm: ', resolve)
  })
  rl.close()

  if (answer !== 'ROLLBACK') {
    console.log('Rollback cancelled.')
    process.exit(0)
  }

  console.log('\nDeleting data...')

  // Delete in reverse order of foreign key dependencies
  await db.delete(dailyStats)
  console.log('  ✓ Deleted daily_stats')

  await db.delete(conversations)
  console.log('  ✓ Deleted conversations')

  await db.delete(salesReps)
  console.log('  ✓ Deleted sales_reps')

  await db.delete(leads)
  console.log('  ✓ Deleted leads')

  console.log('\n✅ Rollback complete!')
}

rollback().catch(console.error)
```

### 5. 建立遷移指南

```markdown
<!-- /home/user/Sales_ai_automation_v3/docs/MIGRATION_GUIDE.md -->
# 資料遷移指南

## 前置條件

1. 確認 V3 專案已完成設定
2. 確認 PostgreSQL (Neon) 資料庫已建立
3. 確認有舊專案 GCP credentials

## 環境變數

```bash
# 舊專案 GCP
export GCP_PROJECT_ID=your-project-id
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# 新專案 PostgreSQL
export DATABASE_URL=postgres://...
```

## 執行遷移

### Step 1: 備份 Firestore

建議在執行前先備份 Firestore 資料：
- GCP Console > Firestore > Export

### Step 2: 執行遷移

```bash
cd /home/user/Sales_ai_automation_v3
bun run scripts/migrate-data.ts
```

### Step 3: 驗證遷移

```bash
bun run scripts/validate-migration.ts
```

### Step 4: 如需回滾

```bash
bun run scripts/rollback-migration.ts
```

## 資料對應表

### Leads

| Firestore | PostgreSQL | 說明 |
|-----------|------------|------|
| id | id | 主鍵 |
| email | email | Email |
| name | name | 名稱 |
| company | company | 公司 |
| phone | phone | 電話 |
| title | title | 職稱 |
| source | source | 來源 |
| status | status | 狀態 |
| score | score | 分數 |
| salesforce_id | salesforceId | Salesforce ID |
| tags | tags | 標籤 (JSON) |
| utm.source | utmSource | UTM Source |
| created_at | createdAt | 建立時間 |

### Conversations

| Firestore | PostgreSQL | 說明 |
|-----------|------------|------|
| sales_cases.id | id | 主鍵 |
| lead_id | leadId | 關聯潛客 |
| sales_rep_id | salesRepId | 業務員 ID |
| sales_rep_name | salesRepName | 業務員名稱 |
| status | status | 狀態 |
| transcript.full_text | transcriptFullText | 逐字稿 |
| transcript.segments | transcriptSegments | 片段 (JSON) |
| cases.analysis.agents.agent2.meddic_score | meddicScore | MEDDIC 分數 |
| cases.analysis.agents.agent4.executive_summary | summary | 摘要 |
| cases.analysis.agents | analysisRaw | 原始分析 (JSON) |

## 注意事項

1. 遷移是冪等的（可重複執行）
2. 使用 `onConflictDoNothing` 避免重複
3. Firestore 資料不會被修改
4. 遷移失敗可使用 rollback 腳本
```

### 6. 建立完成報告

建立 `/home/user/Sales_ai_automation_v3/scripts/AGENT_H_COMPLETE.md`：

```markdown
# Agent H 完成報告

## 建立的腳本

| 檔案 | 說明 |
|------|------|
| migrate-data.ts | 主遷移腳本 |
| validate-migration.ts | 驗證腳本 |
| rollback-migration.ts | 回滾腳本 |

## 資料對應

### Collections

| Firestore Collection | PostgreSQL Table |
|---------------------|------------------|
| leads | leads |
| sales_cases | conversations |
| cases (analysis) | conversations.analysisRaw |
| (extracted) | sales_reps |

### 欄位轉換

- Timestamp → timestamp
- Nested objects → JSONB
- Arrays → JSON string

## 執行步驟

1. 設定環境變數
2. 執行 `bun run scripts/migrate-data.ts`
3. 執行 `bun run scripts/validate-migration.ts`

## 測試結果

（如果有執行測試，記錄結果）

## 注意事項

（記錄任何問題或特殊處理）
```

## 完成標準

- [ ] migrate-data.ts 建立
- [ ] validate-migration.ts 建立
- [ ] rollback-migration.ts 建立
- [ ] MIGRATION_GUIDE.md 建立
- [ ] 腳本可正常執行（語法正確）
- [ ] 完成報告建立
