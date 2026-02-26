# Agent G: Integration

## 任務說明

你是 Integration Agent，負責整合所有模組並確保系統正常運作。

## 前置條件

**必須等待 Agent D, E, F 全部完成**

檢查以下檔案存在：
- `/home/user/Sales_ai_automation_v3/apps/server/src/routers/AGENT_D_COMPLETE.md`
- `/home/user/Sales_ai_automation_v3/apps/web/src/routes/AGENT_E_COMPLETE.md`
- `/home/user/Sales_ai_automation_v3/apps/server/src/slack/AGENT_F_COMPLETE.md`

## 任務清單

### 1. 整合後端入口

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/index.ts
import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { logger } from 'hono/logger'
import { createORPCHandler } from '@orpc/server/hono'
import { appRouter } from './routers'
import { initSlackBot } from './slack'
import { validateEnv } from './env'

// Validate environment variables
validateEnv()

const app = new Hono()

// Middleware
app.use('*', logger())
app.use('*', cors({
  origin: [
    'http://localhost:5173',
    'http://localhost:3000',
    process.env.WEB_APP_URL ?? '',
  ].filter(Boolean),
  credentials: true,
}))

// Health check (outside oRPC for simplicity)
app.get('/health', (c) => {
  return c.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '3.0.0',
  })
})

// oRPC handler
app.route('/api', createORPCHandler({ router: appRouter }))

// Start Slack bot (only in non-worker environments)
if (typeof process !== 'undefined' && process.env.ENABLE_SLACK_BOT === 'true') {
  initSlackBot().catch(console.error)
}

export default app

// For Cloudflare Workers
export { app }
```

### 2. 建立 Database Client Export

```typescript
// /home/user/Sales_ai_automation_v3/packages/db/src/client.ts
import { drizzle } from 'drizzle-orm/neon-http'
import { neon } from '@neondatabase/serverless'
import * as schema from './schema'

const sql = neon(process.env.DATABASE_URL!)

export const db = drizzle(sql, { schema })

export type Database = typeof db
```

更新 index：
```typescript
// /home/user/Sales_ai_automation_v3/packages/db/src/index.ts
export * from './schema'
export * from './client'
```

### 3. 確認前端 API 連接

檢查 `/home/user/Sales_ai_automation_v3/apps/web/src/lib/api.ts` 正確設定：

```typescript
import { createORPCClient } from '@orpc/client'
import { createORPCReact } from '@orpc/react'
import type { AppRouter } from '@sales-ai/server'

const client = createORPCClient<AppRouter>({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:3000/api',
})

export const orpc = createORPCReact(client)
```

### 4. 建立完整處理流程

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/workflows/analyze-conversation.ts
import { db } from '@sales-ai/db'
import { conversations } from '@sales-ai/db/schema'
import { eq } from 'drizzle-orm'
import { transcriptionService } from '../services/transcription'
import { storageService } from '../services/storage'
import { llmService } from '../services/llm'

export interface AnalyzeConversationInput {
  conversationId: string
  audioBuffer: ArrayBuffer
  fileName: string
  salesRepName?: string
}

export async function analyzeConversation(input: AnalyzeConversationInput) {
  const { conversationId, audioBuffer, fileName, salesRepName } = input

  try {
    // 1. Update status to transcribing
    await db.update(conversations)
      .set({ status: 'transcribing', updatedAt: new Date() })
      .where(eq(conversations.id, conversationId))

    // 2. Upload audio to storage
    const audioKey = await storageService.uploadAudio(`${conversationId}.mp4`, audioBuffer)

    // 3. Transcribe
    const transcription = await transcriptionService.transcribe(audioBuffer, fileName)

    // 4. Save transcription
    await db.update(conversations).set({
      transcriptFullText: transcription.text,
      transcriptSegments: transcription.segments,
      transcriptLanguage: transcription.language,
      audioDurationSeconds: transcription.duration,
      audioFileUri: audioKey,
      status: 'analyzing',
      updatedAt: new Date(),
    }).where(eq(conversations.id, conversationId))

    // 5. Analyze with LLM
    const analysis = await runLLMAnalysis(transcription.text)

    // 6. Save analysis
    await db.update(conversations).set({
      meddicScore: analysis.meddicScore,
      progressScore: analysis.progressScore,
      qualificationStatus: analysis.qualificationStatus,
      summary: analysis.summary,
      customerSummary: analysis.customerSummary,
      analysisRaw: analysis,
      status: 'completed',
      completedAt: new Date(),
      analyzedAt: new Date(),
      updatedAt: new Date(),
    }).where(eq(conversations.id, conversationId))

    return { success: true, conversationId, analysis }

  } catch (error) {
    // Update status to failed
    await db.update(conversations)
      .set({ status: 'failed', updatedAt: new Date() })
      .where(eq(conversations.id, conversationId))

    throw error
  }
}

async function runLLMAnalysis(transcript: string) {
  const prompt = `
你是專業的銷售對話分析師。請分析以下銷售對話，評估 MEDDIC 方法論的各項指標。

對話內容：
${transcript}

請以 JSON 格式回應，包含以下欄位：
- meddicScore: 0-100 的整體 MEDDIC 分數
- progressScore: 0-100 的推進分數
- qualificationStatus: "qualified" | "unqualified" | "needs_work"
- summary: 200字以內的銷售摘要（給銷售主管看）
- customerSummary: 150字以內的客戶摘要（可發送給客戶）
- meddic: {
    metrics: 量化指標評估
    economicBuyer: 經濟決策者識別
    decisionCriteria: 決策標準
    decisionProcess: 決策流程
    identifyPain: 痛點識別
    champion: 支持者識別
  }
- buyerSignals: 買家訊號陣列
- coachingNotes: 給銷售的建議陣列
`

  const schema = {
    type: 'object',
    properties: {
      meddicScore: { type: 'number' },
      progressScore: { type: 'number' },
      qualificationStatus: { type: 'string' },
      summary: { type: 'string' },
      customerSummary: { type: 'string' },
      meddic: {
        type: 'object',
        properties: {
          metrics: { type: 'string' },
          economicBuyer: { type: 'string' },
          decisionCriteria: { type: 'string' },
          decisionProcess: { type: 'string' },
          identifyPain: { type: 'string' },
          champion: { type: 'string' },
        },
      },
      buyerSignals: { type: 'array', items: { type: 'string' } },
      coachingNotes: { type: 'array', items: { type: 'string' } },
    },
    required: ['meddicScore', 'progressScore', 'qualificationStatus', 'summary'],
  }

  return llmService.generateStructured(prompt, schema)
}
```

### 5. 建立環境變數範例

```bash
# /home/user/Sales_ai_automation_v3/.env.example

# Database
DATABASE_URL=postgres://user:password@host.neon.tech/database

# LLM
GEMINI_API_KEY=your-gemini-api-key

# Transcription
GROQ_API_KEY=your-groq-api-key

# Slack
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token
ENABLE_SLACK_BOT=true

# Storage (Cloudflare R2)
R2_ENDPOINT=https://account-id.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=sales-ai-audio
R2_PUBLIC_URL=https://your-public-url

# App
WEB_APP_URL=https://your-app.pages.dev
VITE_API_URL=https://your-api.workers.dev/api
```

### 6. 建立測試

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/__tests__/routers.test.ts
import { describe, it, expect } from 'bun:test'
import { appRouter } from '../routers'

describe('Health Router', () => {
  it('should return healthy status', async () => {
    const result = await appRouter.health.check({})
    expect(result.status).toBe('healthy')
  })
})

// Add more tests as needed
```

### 7. 驗證整合

執行以下驗證：

```bash
cd /home/user/Sales_ai_automation_v3

# 1. 檢查 TypeScript 編譯
bun run typecheck

# 2. 啟動開發伺服器
bun run dev

# 3. 測試 API
curl http://localhost:3000/health

# 4. 測試前端
# 開啟 http://localhost:5173
```

### 8. 建立完成報告

建立 `/home/user/Sales_ai_automation_v3/AGENT_G_COMPLETE.md`：

```markdown
# Agent G 完成報告

## 整合架構

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│                  localhost:5173                          │
└─────────────────────┬───────────────────────────────────┘
                      │ oRPC
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend (Hono)                        │
│                  localhost:3000                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │                 oRPC Router                      │    │
│  │  • health    • conversations                    │    │
│  │  • leads     • analytics                        │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │                 Services                         │    │
│  │  • LLM (Gemini)  • Transcription (Groq)        │    │
│  │  • Storage (R2)  • Slack Bot                   │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL (Neon)                           │
└─────────────────────────────────────────────────────────┘
```

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /health | 健康檢查 |
| POST | /api/* | oRPC 端點 |

## 驗證結果

- [ ] TypeScript 編譯成功
- [ ] 後端啟動成功
- [ ] 前端啟動成功
- [ ] API 呼叫成功
- [ ] 資料庫連線成功

## 已知問題

（記錄任何問題）

## 下一步

- Agent H: 資料遷移
```

## 完成標準

- [ ] index.ts 整合完成
- [ ] Database client 建立
- [ ] 環境變數範例建立
- [ ] Workflow 建立
- [ ] 前後端可正常啟動
- [ ] API 可正常呼叫
- [ ] 完成報告建立
