# Agent C: External Services

## 任務說明

你是 External Services Agent，負責建立外部服務整合層（LLM、轉錄、儲存）。

## 前置條件

- 專案 `/home/user/Sales_ai_automation_v3` 已建立
- `bun install` 已執行

## 任務清單

### 1. 閱讀舊專案服務整合

```
/home/user/sales-ai-automation-V2/core/llm/client.py
/home/user/sales-ai-automation-V2/infrastructure/services/transcription/
```

### 2. 安裝依賴

```bash
cd /home/user/Sales_ai_automation_v3/apps/server
bun add @google/generative-ai groq-sdk @aws-sdk/client-s3
```

### 3. 建立環境變數類型

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/env.ts
import { z } from 'zod'

const envSchema = z.object({
  DATABASE_URL: z.string(),
  GEMINI_API_KEY: z.string(),
  GROQ_API_KEY: z.string(),
  SLACK_BOT_TOKEN: z.string(),
  SLACK_SIGNING_SECRET: z.string(),
  SLACK_APP_TOKEN: z.string(),
  R2_ENDPOINT: z.string(),
  R2_ACCESS_KEY_ID: z.string(),
  R2_SECRET_ACCESS_KEY: z.string(),
  R2_BUCKET_NAME: z.string(),
})

export type Env = z.infer<typeof envSchema>

export function validateEnv(): Env {
  const result = envSchema.safeParse(process.env)
  if (!result.success) {
    console.error('Environment validation failed:', result.error.format())
    throw new Error('Invalid environment variables')
  }
  return result.data
}
```

### 4. 建立 LLM Service

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/services/llm.ts
import { GoogleGenerativeAI, type GenerativeModel } from '@google/generative-ai'

let genAI: GoogleGenerativeAI | null = null

function getGenAI(): GoogleGenerativeAI {
  if (!genAI) {
    genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!)
  }
  return genAI
}

export interface GenerateOptions {
  model?: string
  temperature?: number
  maxTokens?: number
  systemInstruction?: string
}

export const llmService = {
  async generate(prompt: string, options: GenerateOptions = {}): Promise<string> {
    const model = getGenAI().getGenerativeModel({
      model: options.model ?? 'gemini-2.0-flash',
      systemInstruction: options.systemInstruction,
    })

    const result = await model.generateContent({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: options.temperature ?? 0.3,
        maxOutputTokens: options.maxTokens ?? 8192,
      },
    })

    return result.response.text()
  },

  async generateStructured<T>(
    prompt: string,
    schema: object,
    options: GenerateOptions = {}
  ): Promise<T> {
    const model = getGenAI().getGenerativeModel({
      model: options.model ?? 'gemini-2.0-flash',
      systemInstruction: options.systemInstruction,
      generationConfig: {
        responseMimeType: 'application/json',
        responseSchema: schema as any,
      },
    })

    const result = await model.generateContent(prompt)
    return JSON.parse(result.response.text())
  },

  async countTokens(text: string, model = 'gemini-2.0-flash'): Promise<number> {
    const modelInstance = getGenAI().getGenerativeModel({ model })
    const result = await modelInstance.countTokens(text)
    return result.totalTokens
  },
}
```

### 5. 建立 Transcription Service

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/services/transcription.ts
import Groq from 'groq-sdk'

let groqClient: Groq | null = null

function getGroqClient(): Groq {
  if (!groqClient) {
    groqClient = new Groq({ apiKey: process.env.GROQ_API_KEY })
  }
  return groqClient
}

export interface TranscriptSegment {
  text: string
  start: number
  end: number
}

export interface TranscriptionResult {
  text: string
  segments: TranscriptSegment[]
  duration: number
  language: string
}

export const transcriptionService = {
  async transcribe(
    audioBuffer: ArrayBuffer,
    filename: string,
    language = 'zh'
  ): Promise<TranscriptionResult> {
    const file = new File([audioBuffer], filename, { type: 'audio/mp4' })

    const transcription = await getGroqClient().audio.transcriptions.create({
      file,
      model: 'whisper-large-v3',
      language,
      response_format: 'verbose_json',
    })

    return {
      text: transcription.text,
      segments:
        transcription.segments?.map((seg) => ({
          text: seg.text,
          start: seg.start,
          end: seg.end,
        })) ?? [],
      duration: transcription.duration ?? 0,
      language: transcription.language ?? language,
    }
  },
}
```

### 6. 建立 Storage Service

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/services/storage.ts
import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  DeleteObjectCommand,
} from '@aws-sdk/client-s3'

let r2Client: S3Client | null = null

function getR2Client(): S3Client {
  if (!r2Client) {
    r2Client = new S3Client({
      region: 'auto',
      endpoint: process.env.R2_ENDPOINT,
      credentials: {
        accessKeyId: process.env.R2_ACCESS_KEY_ID!,
        secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
      },
    })
  }
  return r2Client
}

function getBucketName(): string {
  return process.env.R2_BUCKET_NAME!
}

export const storageService = {
  async uploadAudio(key: string, buffer: ArrayBuffer): Promise<string> {
    const fullKey = `audio/${key}`

    await getR2Client().send(
      new PutObjectCommand({
        Bucket: getBucketName(),
        Key: fullKey,
        Body: Buffer.from(buffer),
        ContentType: 'audio/mp4',
      })
    )

    return fullKey
  },

  async getAudio(key: string): Promise<ReadableStream | null> {
    try {
      const response = await getR2Client().send(
        new GetObjectCommand({
          Bucket: getBucketName(),
          Key: key,
        })
      )
      return response.Body as ReadableStream
    } catch (error) {
      console.error('Failed to get audio:', error)
      return null
    }
  },

  async deleteAudio(key: string): Promise<boolean> {
    try {
      await getR2Client().send(
        new DeleteObjectCommand({
          Bucket: getBucketName(),
          Key: key,
        })
      )
      return true
    } catch (error) {
      console.error('Failed to delete audio:', error)
      return false
    }
  },

  getPublicUrl(key: string): string {
    // R2 public URL format (if public access enabled)
    return `${process.env.R2_PUBLIC_URL}/${key}`
  },
}
```

### 7. 建立 Services Index

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/services/index.ts
export * from './llm'
export * from './transcription'
export * from './storage'
```

### 8. 建立完成報告

建立 `/home/user/Sales_ai_automation_v3/apps/server/src/services/AGENT_C_COMPLETE.md`：

```markdown
# Agent C 完成報告

## 建立的服務

### LLM Service (llm.ts)

| 方法 | 說明 |
|------|------|
| generate() | 生成文字回應 |
| generateStructured<T>() | 生成結構化 JSON |
| countTokens() | 計算 token 數 |

### Transcription Service (transcription.ts)

| 方法 | 說明 |
|------|------|
| transcribe() | 音檔轉文字 |

### Storage Service (storage.ts)

| 方法 | 說明 |
|------|------|
| uploadAudio() | 上傳音檔到 R2 |
| getAudio() | 取得音檔 |
| deleteAudio() | 刪除音檔 |
| getPublicUrl() | 取得公開 URL |

## 環境變數需求

| 變數 | 說明 |
|------|------|
| GEMINI_API_KEY | Google Gemini API Key |
| GROQ_API_KEY | Groq API Key |
| R2_ENDPOINT | R2 Endpoint URL |
| R2_ACCESS_KEY_ID | R2 Access Key |
| R2_SECRET_ACCESS_KEY | R2 Secret Key |
| R2_BUCKET_NAME | R2 Bucket 名稱 |

## 使用範例

```typescript
import { llmService, transcriptionService, storageService } from './services'

// LLM
const response = await llmService.generate('Summarize this conversation...')

// Transcription
const result = await transcriptionService.transcribe(audioBuffer, 'call.mp4')

// Storage
const key = await storageService.uploadAudio('call-001.mp4', buffer)
```

## 注意事項

（記錄任何問題或特殊處理）
```

## 完成標準

- [ ] env.ts 建立
- [ ] llm.ts 建立並可正常呼叫 Gemini
- [ ] transcription.ts 建立
- [ ] storage.ts 建立
- [ ] index.ts 正確導出
- [ ] 完成報告建立
