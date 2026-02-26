# Agent I: Deployment & Testing

## 任務說明

你是 Deployment Agent，負責設定部署配置和執行最終測試。

## 前置條件

**必須等待 Agent H 完成**

檢查：`/home/user/Sales_ai_automation_v3/scripts/AGENT_H_COMPLETE.md` 存在

## 任務清單

### 1. 更新 Cloudflare Workers 配置

```toml
# /home/user/Sales_ai_automation_v3/apps/server/wrangler.toml
name = "sales-ai-api"
main = "src/index.ts"
compatibility_date = "2024-01-01"
compatibility_flags = ["nodejs_compat"]

[vars]
ENVIRONMENT = "production"

# R2 Bucket binding
[[r2_buckets]]
binding = "R2_BUCKET"
bucket_name = "sales-ai-audio"

# Secrets (set via wrangler secret put)
# - DATABASE_URL
# - GEMINI_API_KEY
# - GROQ_API_KEY
# - SLACK_BOT_TOKEN
# - SLACK_SIGNING_SECRET
# - SLACK_APP_TOKEN

[env.production]
name = "sales-ai-api-prod"

[env.staging]
name = "sales-ai-api-staging"
```

### 2. 建立 Cloudflare Pages 配置

```toml
# /home/user/Sales_ai_automation_v3/apps/web/wrangler.toml
name = "sales-ai-web"
compatibility_date = "2024-01-01"

[site]
bucket = "./dist"

[env.production]
name = "sales-ai-web-prod"

[env.staging]
name = "sales-ai-web-staging"
```

### 3. 建立 GitHub Actions CI/CD

```yaml
# /home/user/Sales_ai_automation_v3/.github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: oven-sh/setup-bun@v1
        with:
          bun-version: latest

      - name: Install dependencies
        run: bun install

      - name: Type check
        run: bun run typecheck

      - name: Lint
        run: bun run lint

      - name: Test
        run: bun run test
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4

      - uses: oven-sh/setup-bun@v1
        with:
          bun-version: latest

      - name: Install dependencies
        run: bun install

      - name: Build
        run: bun run build
```

```yaml
# /home/user/Sales_ai_automation_v3/.github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: oven-sh/setup-bun@v1
        with:
          bun-version: latest

      - name: Install dependencies
        run: bun install

      - name: Deploy to Cloudflare Workers
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          workingDirectory: apps/server
          command: deploy --env production

  deploy-web:
    runs-on: ubuntu-latest
    needs: deploy-api
    steps:
      - uses: actions/checkout@v4

      - uses: oven-sh/setup-bun@v1
        with:
          bun-version: latest

      - name: Install dependencies
        run: bun install

      - name: Build web app
        run: bun run build --filter=@sales-ai/web
        env:
          VITE_API_URL: ${{ secrets.PRODUCTION_API_URL }}

      - name: Deploy to Cloudflare Pages
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          workingDirectory: apps/web
          command: pages deploy dist --project-name=sales-ai-web
```

### 4. 建立部署腳本

```bash
#!/bin/bash
# /home/user/Sales_ai_automation_v3/scripts/deploy.sh

set -e

echo "🚀 Starting deployment..."

# Check if logged in to Cloudflare
if ! bunx wrangler whoami > /dev/null 2>&1; then
  echo "Please login to Cloudflare first: bunx wrangler login"
  exit 1
fi

# Set secrets (first time only)
setup_secrets() {
  echo "Setting up secrets..."
  cd apps/server

  echo "Enter DATABASE_URL:"
  bunx wrangler secret put DATABASE_URL

  echo "Enter GEMINI_API_KEY:"
  bunx wrangler secret put GEMINI_API_KEY

  echo "Enter GROQ_API_KEY:"
  bunx wrangler secret put GROQ_API_KEY

  echo "Enter SLACK_BOT_TOKEN:"
  bunx wrangler secret put SLACK_BOT_TOKEN

  echo "Enter SLACK_SIGNING_SECRET:"
  bunx wrangler secret put SLACK_SIGNING_SECRET

  echo "Enter SLACK_APP_TOKEN:"
  bunx wrangler secret put SLACK_APP_TOKEN

  cd ../..
}

# Deploy API
deploy_api() {
  echo "📦 Deploying API to Cloudflare Workers..."
  cd apps/server
  bunx wrangler deploy
  cd ../..
}

# Deploy Web
deploy_web() {
  echo "📦 Building and deploying Web to Cloudflare Pages..."
  bun run build --filter=@sales-ai/web
  cd apps/web
  bunx wrangler pages deploy dist --project-name=sales-ai-web
  cd ../..
}

# Main
case "$1" in
  secrets)
    setup_secrets
    ;;
  api)
    deploy_api
    ;;
  web)
    deploy_web
    ;;
  all)
    deploy_api
    deploy_web
    ;;
  *)
    echo "Usage: $0 {secrets|api|web|all}"
    exit 1
    ;;
esac

echo "✅ Deployment complete!"
```

### 5. 建立健康檢查端點

更新 `/home/user/Sales_ai_automation_v3/apps/server/src/routers/health.ts`：

```typescript
import { os } from '@orpc/server'
import { db } from '@sales-ai/db'
import { sql } from 'drizzle-orm'

export const healthRouter = os.router({
  check: os.handler(async () => {
    const checks = {
      api: 'healthy',
      database: 'unknown',
      timestamp: new Date().toISOString(),
      version: '3.0.0',
    }

    // Check database
    try {
      await db.execute(sql`SELECT 1`)
      checks.database = 'healthy'
    } catch (error) {
      checks.database = 'unhealthy'
    }

    return checks
  }),

  ready: os.handler(async () => {
    // Readiness check - all dependencies must be available
    try {
      await db.execute(sql`SELECT 1`)
      return { ready: true }
    } catch (error) {
      return { ready: false, error: 'Database unavailable' }
    }
  }),

  live: os.handler(async () => {
    // Liveness check - just confirm the app is running
    return { alive: true }
  }),
})
```

### 6. 建立錯誤追蹤

```typescript
// /home/user/Sales_ai_automation_v3/apps/server/src/lib/error-handler.ts
import { HTTPException } from 'hono/http-exception'

export class AppError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500
  ) {
    super(message)
    this.name = 'AppError'
  }
}

export function handleError(error: unknown) {
  console.error('Error:', error)

  if (error instanceof AppError) {
    return {
      error: {
        code: error.code,
        message: error.message,
      },
      status: error.statusCode,
    }
  }

  if (error instanceof HTTPException) {
    return {
      error: {
        code: 'HTTP_ERROR',
        message: error.message,
      },
      status: error.status,
    }
  }

  if (error instanceof Error) {
    return {
      error: {
        code: 'INTERNAL_ERROR',
        message: process.env.NODE_ENV === 'production'
          ? 'Internal server error'
          : error.message,
      },
      status: 500,
    }
  }

  return {
    error: {
      code: 'UNKNOWN_ERROR',
      message: 'An unknown error occurred',
    },
    status: 500,
  }
}
```

### 7. 建立部署文檔

```markdown
<!-- /home/user/Sales_ai_automation_v3/docs/DEPLOYMENT.md -->
# 部署指南

## 架構

```
┌─────────────────────────────────────────────────────────┐
│                    Cloudflare CDN                        │
└───────────────────────┬─────────────────────────────────┘
                        │
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
┌──────────────────┐       ┌──────────────────┐
│  Cloudflare      │       │  Cloudflare      │
│  Pages           │       │  Workers         │
│  (Frontend)      │       │  (API)           │
│  sales-ai-web    │       │  sales-ai-api    │
└──────────────────┘       └────────┬─────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │   Neon    │   │   R2      │   │  External │
            │PostgreSQL │   │  Storage  │   │  APIs     │
            └───────────┘   └───────────┘   └───────────┘
```

## 環境

| 環境 | API URL | Web URL |
|------|---------|---------|
| Production | sales-ai-api.workers.dev | sales-ai-web.pages.dev |
| Staging | sales-ai-api-staging.workers.dev | sales-ai-web-staging.pages.dev |

## 首次部署

### 1. 登入 Cloudflare

```bash
bunx wrangler login
```

### 2. 設定 Secrets

```bash
./scripts/deploy.sh secrets
```

### 3. 部署

```bash
./scripts/deploy.sh all
```

## 日常部署

推送到 `main` 分支會自動觸發 GitHub Actions 部署。

手動部署：

```bash
# 只部署 API
./scripts/deploy.sh api

# 只部署 Web
./scripts/deploy.sh web

# 全部部署
./scripts/deploy.sh all
```

## 環境變數

### Workers (API)

| 變數 | 說明 | 設定方式 |
|------|------|----------|
| DATABASE_URL | PostgreSQL 連線字串 | Secret |
| GEMINI_API_KEY | Gemini API Key | Secret |
| GROQ_API_KEY | Groq API Key | Secret |
| SLACK_BOT_TOKEN | Slack Bot Token | Secret |
| SLACK_SIGNING_SECRET | Slack Signing Secret | Secret |
| SLACK_APP_TOKEN | Slack App Token | Secret |

### Pages (Web)

| 變數 | 說明 | 設定方式 |
|------|------|----------|
| VITE_API_URL | API URL | Build env |

## 監控

### Health Check

```bash
curl https://sales-ai-api.workers.dev/health
```

### Logs

```bash
bunx wrangler tail sales-ai-api
```

## 回滾

```bash
# 查看部署歷史
bunx wrangler deployments list

# 回滾到特定版本
bunx wrangler rollback [deployment-id]
```

## 疑難排解

### API 500 錯誤

1. 檢查 logs: `bunx wrangler tail`
2. 確認環境變數設定正確
3. 確認資料庫連線

### 前端載入失敗

1. 確認 VITE_API_URL 正確
2. 檢查 CORS 設定
3. 確認 API 可存取
```

### 8. 建立完成報告

建立 `/home/user/Sales_ai_automation_v3/AGENT_I_COMPLETE.md`：

```markdown
# Agent I 完成報告

## 部署配置

| 檔案 | 說明 |
|------|------|
| apps/server/wrangler.toml | Workers 配置 |
| apps/web/wrangler.toml | Pages 配置 |
| .github/workflows/ci.yml | CI 流程 |
| .github/workflows/deploy.yml | CD 流程 |
| scripts/deploy.sh | 部署腳本 |

## 環境變數清單

### Secrets (需手動設定)

- DATABASE_URL
- GEMINI_API_KEY
- GROQ_API_KEY
- SLACK_BOT_TOKEN
- SLACK_SIGNING_SECRET
- SLACK_APP_TOKEN

### GitHub Secrets

- CLOUDFLARE_API_TOKEN
- PRODUCTION_API_URL

## 部署驗證清單

- [ ] `bunx wrangler login` 成功
- [ ] Secrets 設定完成
- [ ] API 部署成功
- [ ] Web 部署成功
- [ ] Health check 通過
- [ ] 前端可正常載入
- [ ] API 可正常呼叫

## 部署 URL

- API: https://sales-ai-api.workers.dev
- Web: https://sales-ai-web.pages.dev

## 注意事項

（記錄任何問題或特殊處理）
```

## 完成標準

- [ ] wrangler.toml 配置完成
- [ ] GitHub Actions 建立
- [ ] 部署腳本建立
- [ ] 健康檢查端點更新
- [ ] 錯誤處理建立
- [ ] 部署文檔建立
- [ ] 完成報告建立
