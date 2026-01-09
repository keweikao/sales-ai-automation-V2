# Agent F: Slack Bot

## 任務說明

你是 Slack Bot Agent，負責建立 Slack Bot 整合。

## 前置條件

**必須等待 Agent C 完成**

檢查：`/home/user/Sales_ai_automation_v3/apps/server/src/services/AGENT_C_COMPLETE.md` 存在

## 任務清單

### 1. 閱讀舊專案 Slack Bot

```
/home/user/sales-ai-automation-V2/modules/03-sales-conversation/slack_bot/
```

### 2. 安裝依賴

```bash
cd /home/user/Sales_ai_automation_v3/apps/server
bun add @slack/bolt @slack/web-api
```

### 3. 建立 Slack App

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/slack/app.ts
import { App, LogLevel } from '@slack/bolt'

let slackApp: App | null = null

export function getSlackApp(): App {
  if (!slackApp) {
    slackApp = new App({
      token: process.env.SLACK_BOT_TOKEN,
      signingSecret: process.env.SLACK_SIGNING_SECRET,
      socketMode: true,
      appToken: process.env.SLACK_APP_TOKEN,
      logLevel: LogLevel.INFO,
    })
  }
  return slackApp
}

export async function startSlackApp() {
  const app = getSlackApp()
  await app.start()
  console.log('⚡️ Slack Bot is running!')
}
```

### 4. 建立 File Upload Handler

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/slack/handlers/file-upload.ts
import { getSlackApp } from '../app'
import { processAudioFile } from '../workflows/process-audio'

export function registerFileUploadHandler() {
  const app = getSlackApp()

  // Listen for file_shared events
  app.event('file_shared', async ({ event, client }) => {
    try {
      // Get file info
      const fileInfo = await client.files.info({ file: event.file_id })
      const file = fileInfo.file

      if (!file) {
        console.log('File info not found')
        return
      }

      // Check if it's an audio file
      const audioMimeTypes = ['audio/mp4', 'audio/mpeg', 'audio/wav', 'audio/m4a', 'audio/ogg']
      if (!file.mimetype || !audioMimeTypes.includes(file.mimetype)) {
        console.log(`Skipping non-audio file: ${file.mimetype}`)
        return
      }

      console.log(`Processing audio file: ${file.name}`)

      // Get user info for sales rep name
      const userInfo = await client.users.info({ user: event.user_id })
      const salesRepName = userInfo.user?.real_name ?? userInfo.user?.name ?? 'Unknown'

      // Send processing message
      const channel = event.channel_id
      await client.chat.postMessage({
        channel,
        text: `🎙️ 收到音檔 \`${file.name}\`，正在處理中...`,
      })

      // Process the audio file
      await processAudioFile({
        fileId: event.file_id,
        fileName: file.name ?? 'audio.mp4',
        fileUrl: file.url_private_download ?? '',
        channelId: channel,
        userId: event.user_id,
        salesRepName,
        slackToken: process.env.SLACK_BOT_TOKEN!,
      })

    } catch (error) {
      console.error('Error handling file upload:', error)
    }
  })
}
```

### 5. 建立 Message Handler

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/slack/handlers/messages.ts
import { getSlackApp } from '../app'
import { db } from '@sales-ai/db'
import { conversations } from '@sales-ai/db/schema'
import { desc, eq } from 'drizzle-orm'

export function registerMessageHandlers() {
  const app = getSlackApp()

  // Help command
  app.message(/^(help|幫助|指令)$/i, async ({ message, say }) => {
    await say({
      blocks: [
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: '*Sales AI Bot 指令*\n\n' +
              '• 上傳音檔 - 自動分析銷售對話\n' +
              '• `最近` - 查看最近的分析\n' +
              '• `統計` - 查看統計資料\n' +
              '• `help` - 顯示此說明',
          },
        },
      ],
    })
  })

  // Recent analyses
  app.message(/^(最近|recent)$/i, async ({ message, say }) => {
    const recentConvs = await db
      .select()
      .from(conversations)
      .where(eq(conversations.status, 'completed'))
      .orderBy(desc(conversations.createdAt))
      .limit(5)

    if (recentConvs.length === 0) {
      await say('目前沒有已完成的分析記錄。')
      return
    }

    const blocks = [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: '*最近 5 筆分析*',
        },
      },
      ...recentConvs.map((conv) => ({
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `• *${conv.salesRepName ?? 'Unknown'}* - MEDDIC: ${conv.meddicScore ?? '-'} - ${conv.createdAt?.toLocaleDateString('zh-TW') ?? '-'}`,
        },
      })),
    ]

    await say({ blocks })
  })

  // Stats command
  app.message(/^(統計|stats)$/i, async ({ message, say }) => {
    // TODO: Implement stats query
    await say('統計功能開發中...')
  })
}
```

### 6. 建立 Analysis Result Blocks

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/slack/blocks/analysis-result.ts
import type { KnownBlock } from '@slack/bolt'

export interface AnalysisResultData {
  conversationId: string
  salesRepName: string
  meddicScore: number
  progressScore: number
  qualificationStatus: string
  summary: string
  keyInsights: string[]
}

export function buildAnalysisResultBlocks(data: AnalysisResultData): KnownBlock[] {
  const scoreEmoji = data.meddicScore >= 70 ? '🟢' : data.meddicScore >= 40 ? '🟡' : '🔴'

  return [
    {
      type: 'header',
      text: {
        type: 'plain_text',
        text: '📊 對話分析完成',
        emoji: true,
      },
    },
    {
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*業務員*\n${data.salesRepName}`,
        },
        {
          type: 'mrkdwn',
          text: `*MEDDIC 分數*\n${scoreEmoji} ${data.meddicScore}/100`,
        },
        {
          type: 'mrkdwn',
          text: `*推進分數*\n${data.progressScore}/100`,
        },
        {
          type: 'mrkdwn',
          text: `*資格狀態*\n${data.qualificationStatus}`,
        },
      ],
    },
    {
      type: 'divider',
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*摘要*\n${data.summary}`,
      },
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*關鍵洞察*\n${data.keyInsights.map((i) => `• ${i}`).join('\n')}`,
      },
    },
    {
      type: 'divider',
    },
    {
      type: 'actions',
      elements: [
        {
          type: 'button',
          text: {
            type: 'plain_text',
            text: '查看詳情',
            emoji: true,
          },
          url: `${process.env.WEB_APP_URL}/conversations/${data.conversationId}`,
          action_id: 'view_details',
        },
        {
          type: 'button',
          text: {
            type: 'plain_text',
            text: '編輯摘要',
            emoji: true,
          },
          action_id: 'edit_summary',
          value: data.conversationId,
        },
      ],
    },
  ]
}
```

### 7. 建立 Audio Processing Workflow

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/slack/workflows/process-audio.ts
import { transcriptionService } from '../../services/transcription'
import { storageService } from '../../services/storage'
import { llmService } from '../../services/llm'
import { db } from '@sales-ai/db'
import { conversations } from '@sales-ai/db/schema'
import { getSlackApp } from '../app'
import { buildAnalysisResultBlocks } from '../blocks/analysis-result'

interface ProcessAudioParams {
  fileId: string
  fileName: string
  fileUrl: string
  channelId: string
  userId: string
  salesRepName: string
  slackToken: string
}

export async function processAudioFile(params: ProcessAudioParams) {
  const app = getSlackApp()
  const conversationId = `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

  try {
    // 1. Create conversation record
    await db.insert(conversations).values({
      id: conversationId,
      salesRepName: params.salesRepName,
      status: 'pending',
    })

    // 2. Download audio from Slack
    const response = await fetch(params.fileUrl, {
      headers: { Authorization: `Bearer ${params.slackToken}` },
    })
    const audioBuffer = await response.arrayBuffer()

    // 3. Upload to R2
    await db.update(conversations)
      .set({ status: 'transcribing' })
      .where(eq(conversations.id, conversationId))

    const audioKey = await storageService.uploadAudio(`${conversationId}.mp4`, audioBuffer)

    // 4. Transcribe
    const transcription = await transcriptionService.transcribe(audioBuffer, params.fileName)

    await db.update(conversations).set({
      transcriptFullText: transcription.text,
      transcriptSegments: transcription.segments,
      audioDurationSeconds: transcription.duration,
      audioFileUri: audioKey,
      status: 'analyzing',
    }).where(eq(conversations.id, conversationId))

    // 5. Analyze with LLM
    const analysisPrompt = `
分析以下銷售對話，評估 MEDDIC 各項指標：

${transcription.text}

請以 JSON 格式回應，包含：
- meddicScore: 0-100
- progressScore: 0-100
- qualificationStatus: "qualified" | "unqualified" | "needs_work"
- summary: 200字以內摘要
- keyInsights: 3-5個關鍵洞察
`

    const analysis = await llmService.generateStructured<{
      meddicScore: number
      progressScore: number
      qualificationStatus: string
      summary: string
      keyInsights: string[]
    }>(analysisPrompt, {
      type: 'object',
      properties: {
        meddicScore: { type: 'number' },
        progressScore: { type: 'number' },
        qualificationStatus: { type: 'string' },
        summary: { type: 'string' },
        keyInsights: { type: 'array', items: { type: 'string' } },
      },
      required: ['meddicScore', 'progressScore', 'qualificationStatus', 'summary', 'keyInsights'],
    })

    // 6. Save analysis
    await db.update(conversations).set({
      meddicScore: analysis.meddicScore,
      progressScore: analysis.progressScore,
      qualificationStatus: analysis.qualificationStatus,
      summary: analysis.summary,
      analysisRaw: analysis,
      status: 'completed',
      completedAt: new Date(),
      analyzedAt: new Date(),
    }).where(eq(conversations.id, conversationId))

    // 7. Send result to Slack
    const blocks = buildAnalysisResultBlocks({
      conversationId,
      salesRepName: params.salesRepName,
      ...analysis,
    })

    await app.client.chat.postMessage({
      channel: params.channelId,
      blocks,
      text: `分析完成！MEDDIC 分數: ${analysis.meddicScore}`,
    })

  } catch (error) {
    console.error('Error processing audio:', error)

    // Update status to failed
    await db.update(conversations)
      .set({ status: 'failed' })
      .where(eq(conversations.id, conversationId))

    // Notify user
    await app.client.chat.postMessage({
      channel: params.channelId,
      text: `❌ 處理音檔時發生錯誤：${error instanceof Error ? error.message : 'Unknown error'}`,
    })
  }
}

// Helper import
import { eq } from 'drizzle-orm'
```

### 8. 建立 Slack Index

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/slack/index.ts
import { startSlackApp, getSlackApp } from './app'
import { registerFileUploadHandler } from './handlers/file-upload'
import { registerMessageHandlers } from './handlers/messages'

export async function initSlackBot() {
  // Register handlers
  registerFileUploadHandler()
  registerMessageHandlers()

  // Start the app
  await startSlackApp()
}

export { getSlackApp } from './app'
export { buildAnalysisResultBlocks } from './blocks/analysis-result'
```

### 9. 建立完成報告

建立 `/home/user/Sales_ai_automation_v3/apps/server/src/slack/AGENT_F_COMPLETE.md`：

```markdown
# Agent F 完成報告

## 建立的檔案

| 檔案 | 說明 |
|------|------|
| app.ts | Slack App 初始化 |
| handlers/file-upload.ts | 音檔上傳處理 |
| handlers/messages.ts | 訊息指令處理 |
| blocks/analysis-result.ts | 分析結果 Block Kit |
| workflows/process-audio.ts | 音檔處理流程 |
| index.ts | 導出入口 |

## 支援的事件

| 事件 | 說明 |
|------|------|
| file_shared | 檔案上傳時觸發 |

## 支援的指令

| 指令 | 說明 |
|------|------|
| help / 幫助 | 顯示說明 |
| 最近 / recent | 查看最近分析 |
| 統計 / stats | 查看統計 |

## 處理流程

```
音檔上傳
    ↓
下載音檔
    ↓
上傳到 R2
    ↓
Groq Whisper 轉錄
    ↓
Gemini LLM 分析
    ↓
儲存結果
    ↓
發送 Slack 訊息
```

## 環境變數需求

| 變數 | 說明 |
|------|------|
| SLACK_BOT_TOKEN | Bot User OAuth Token |
| SLACK_SIGNING_SECRET | Signing Secret |
| SLACK_APP_TOKEN | App-Level Token (Socket Mode) |
| WEB_APP_URL | Web App URL (for links) |

## 注意事項

（記錄任何問題或特殊處理）
```

## 完成標準

- [ ] app.ts 建立
- [ ] file-upload.ts 建立
- [ ] messages.ts 建立
- [ ] analysis-result.ts 建立
- [ ] process-audio.ts 建立
- [ ] index.ts 正確導出
- [ ] 完成報告建立
