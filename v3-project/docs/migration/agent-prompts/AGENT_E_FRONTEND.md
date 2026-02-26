# Agent E: Frontend Pages

## 任務說明

你是 Frontend Pages Agent，負責遷移前端頁面並整合 oRPC client。

## 前置條件

**必須等待 Agent B 完成**

檢查：`/home/user/Sales_ai_automation_v3/packages/ui/AGENT_B_COMPLETE.md` 存在

## 任務清單

### 1. 閱讀舊專案頁面

```
/home/user/sales-ai-automation-V2/dashboard/apps/web/src/routes/
/home/user/sales-ai-automation-V2/dashboard/apps/web/src/components/
```

### 2. 設定 oRPC Client

```typescript
// /home/user/Sales_ai_automation_v3/apps/web/src/lib/api.ts
import { createORPCClient } from '@orpc/client'
import { createORPCReact } from '@orpc/react'
import type { AppRouter } from '@sales-ai/server'

const client = createORPCClient<AppRouter>({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:3000',
})

export const orpc = createORPCReact(client)

// Re-export for convenience
export { client }
```

### 3. 設定 Provider

```typescript
// /home/user/Sales_ai_automation_v3/apps/web/src/lib/providers.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { orpc } from './api'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
})

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <orpc.Provider>
        {children}
      </orpc.Provider>
    </QueryClientProvider>
  )
}
```

### 4. 建立 Dashboard 頁面

```typescript
// /home/user/Sales_ai_automation_v3/apps/web/src/routes/index.tsx
import { createFileRoute } from '@tanstack/react-router'
import { orpc } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, Loading } from '@sales-ai/ui'

export const Route = createFileRoute('/')({
  component: DashboardPage,
})

function DashboardPage() {
  const { data: stats, isLoading, error } = orpc.analytics.dashboard.useQuery()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loading size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8 text-red-500">
        載入失敗: {error.message}
      </div>
    )
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">儀表板</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="總對話數"
          value={stats?.totalConversations ?? 0}
        />
        <StatCard
          title="今日完成"
          value={stats?.completedToday ?? 0}
        />
        <StatCard
          title="待分析"
          value={stats?.pendingAnalysis ?? 0}
        />
        <StatCard
          title="平均 MEDDIC 分數"
          value={stats?.avgMeddicScore ?? 0}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>表現最佳業務員</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats?.topPerformers.map((rep) => (
                <div key={rep.id} className="flex justify-between items-center">
                  <span>{rep.name}</span>
                  <span className="font-medium">{rep.avgMeddicScore} 分</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StatCard({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}
```

### 5. 建立 Conversations List 頁面

```typescript
// /home/user/Sales_ai_automation_v3/apps/web/src/routes/conversations/index.tsx
import { createFileRoute, Link } from '@tanstack/react-router'
import { orpc } from '@/lib/api'
import {
  Card, CardContent, CardHeader, CardTitle,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  Loading, Button,
} from '@sales-ai/ui'

export const Route = createFileRoute('/conversations/')({
  component: ConversationsPage,
})

function ConversationsPage() {
  const { data, isLoading, error } = orpc.conversations.list.useQuery({
    limit: 50,
  })

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loading size="lg" />
      </div>
    )
  }

  if (error) {
    return <div className="p-8 text-red-500">載入失敗: {error.message}</div>
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">對話列表</h1>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>業務員</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead>MEDDIC 分數</TableHead>
                <TableHead>建立時間</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items.map((conversation) => (
                <TableRow key={conversation.id}>
                  <TableCell className="font-mono text-sm">
                    {conversation.id.slice(0, 12)}...
                  </TableCell>
                  <TableCell>{conversation.salesRepName ?? '-'}</TableCell>
                  <TableCell>
                    <StatusBadge status={conversation.status} />
                  </TableCell>
                  <TableCell>
                    {conversation.meddicScore ?? '-'}
                  </TableCell>
                  <TableCell>
                    {conversation.createdAt
                      ? new Date(conversation.createdAt).toLocaleDateString('zh-TW')
                      : '-'}
                  </TableCell>
                  <TableCell>
                    <Link to="/conversations/$id" params={{ id: conversation.id }}>
                      <Button variant="outline" size="sm">
                        查看
                      </Button>
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    transcribing: 'bg-blue-100 text-blue-800',
    analyzing: 'bg-purple-100 text-purple-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] ?? 'bg-gray-100'}`}>
      {status}
    </span>
  )
}
```

### 6. 建立 Conversation Detail 頁面

```typescript
// /home/user/Sales_ai_automation_v3/apps/web/src/routes/conversations/$id.tsx
import { createFileRoute } from '@tanstack/react-router'
import { orpc } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, Loading } from '@sales-ai/ui'

export const Route = createFileRoute('/conversations/$id')({
  component: ConversationDetailPage,
})

function ConversationDetailPage() {
  const { id } = Route.useParams()

  const { data: conversation, isLoading: loadingConv } = orpc.conversations.getById.useQuery({ id })
  const { data: analysis, isLoading: loadingAnalysis } = orpc.conversations.getAnalysis.useQuery({ id })

  if (loadingConv || loadingAnalysis) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loading size="lg" />
      </div>
    )
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">對話詳情</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 基本資訊 */}
        <Card>
          <CardHeader>
            <CardTitle>基本資訊</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <InfoRow label="ID" value={conversation?.id} />
            <InfoRow label="業務員" value={conversation?.salesRepName} />
            <InfoRow label="狀態" value={conversation?.status} />
            <InfoRow label="類型" value={conversation?.conversationType} />
          </CardContent>
        </Card>

        {/* 分析結果 */}
        <Card>
          <CardHeader>
            <CardTitle>分析結果</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <InfoRow label="MEDDIC 分數" value={analysis?.meddicScore} />
            <InfoRow label="推進分數" value={analysis?.progressScore} />
            <InfoRow label="資格狀態" value={analysis?.qualificationStatus} />
          </CardContent>
        </Card>

        {/* 摘要 */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>摘要</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {analysis?.summary ?? '尚無摘要'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 逐字稿 */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>逐字稿</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="whitespace-pre-wrap text-sm">
            {conversation?.transcriptFullText ?? '尚無逐字稿'}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value ?? '-'}</span>
    </div>
  )
}
```

### 7. 建立 Leads 頁面

```typescript
// /home/user/Sales_ai_automation_v3/apps/web/src/routes/leads/index.tsx
import { createFileRoute } from '@tanstack/react-router'
import { orpc } from '@/lib/api'
import {
  Card, CardContent,
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  Loading,
} from '@sales-ai/ui'

export const Route = createFileRoute('/leads/')({
  component: LeadsPage,
})

function LeadsPage() {
  const { data, isLoading, error } = orpc.leads.list.useQuery({ limit: 50 })

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loading size="lg" />
      </div>
    )
  }

  if (error) {
    return <div className="p-8 text-red-500">載入失敗: {error.message}</div>
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">潛客列表</h1>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名稱</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>公司</TableHead>
                <TableHead>狀態</TableHead>
                <TableHead>分數</TableHead>
                <TableHead>來源</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items.map((lead) => (
                <TableRow key={lead.id}>
                  <TableCell>{lead.name ?? '-'}</TableCell>
                  <TableCell>{lead.email}</TableCell>
                  <TableCell>{lead.company ?? '-'}</TableCell>
                  <TableCell>{lead.status}</TableCell>
                  <TableCell>{lead.score}</TableCell>
                  <TableCell>{lead.source}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
```

### 8. 更新 Root Layout

```typescript
// /home/user/Sales_ai_automation_v3/apps/web/src/routes/__root.tsx
import { createRootRoute, Link, Outlet } from '@tanstack/react-router'
import { Providers } from '@/lib/providers'

export const Route = createRootRoute({
  component: RootLayout,
})

function RootLayout() {
  return (
    <Providers>
      <div className="min-h-screen bg-background">
        <nav className="border-b">
          <div className="container mx-auto px-4">
            <div className="flex h-16 items-center space-x-8">
              <Link to="/" className="font-bold text-xl">
                Sales AI
              </Link>
              <Link to="/" className="text-muted-foreground hover:text-foreground">
                儀表板
              </Link>
              <Link to="/conversations" className="text-muted-foreground hover:text-foreground">
                對話
              </Link>
              <Link to="/leads" className="text-muted-foreground hover:text-foreground">
                潛客
              </Link>
            </div>
          </div>
        </nav>
        <main>
          <Outlet />
        </main>
      </div>
    </Providers>
  )
}
```

### 9. 建立完成報告

建立 `/home/user/Sales_ai_automation_v3/apps/web/src/routes/AGENT_E_COMPLETE.md`：

```markdown
# Agent E 完成報告

## 建立的頁面

| 路由 | 檔案 | 說明 |
|------|------|------|
| / | index.tsx | 儀表板 |
| /conversations | conversations/index.tsx | 對話列表 |
| /conversations/:id | conversations/$id.tsx | 對話詳情 |
| /leads | leads/index.tsx | 潛客列表 |

## oRPC 查詢

| 頁面 | 使用的查詢 |
|------|-----------|
| Dashboard | analytics.dashboard |
| Conversations | conversations.list |
| Conversation Detail | conversations.getById, conversations.getAnalysis |
| Leads | leads.list |

## 使用的 UI 元件

- Card, CardContent, CardHeader, CardTitle
- Table, TableBody, TableCell, TableHead, TableHeader, TableRow
- Button
- Loading

## 注意事項

（記錄任何問題或特殊處理）
```

## 完成標準

- [ ] api.ts 建立
- [ ] providers.tsx 建立
- [ ] 所有頁面建立
- [ ] __root.tsx 更新
- [ ] 頁面可正常載入（假設後端可用）
- [ ] 完成報告建立
