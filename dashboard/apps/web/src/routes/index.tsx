import { createFileRoute } from '@tanstack/react-router';
import { Card, CardHeader, CardContent, ScoreGauge, StatusBadge, Badge } from '@sales-ai/ui';
import type { Conversation, PerformerStats } from '@sales-ai/types';
import { useDashboardStats, useTrends, useConversations } from '@/hooks/use-dashboard';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Link } from '@tanstack/react-router';

export const Route = createFileRoute('/')({
  component: DashboardPage,
});

function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: trends, isLoading: trendsLoading } = useTrends('7d');
  const { data: conversations, isLoading: convsLoading } = useConversations({ limit: 5 });

  if (statsLoading || trendsLoading || convsLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-muted-foreground">載入中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">儀表板</h1>
        <p className="text-muted-foreground">銷售對話分析總覽</p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <span className="text-sm font-medium text-muted-foreground">總對話數</span>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats?.totalConversations ?? 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <span className="text-sm font-medium text-muted-foreground">今日完成</span>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{stats?.completedToday ?? 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <span className="text-sm font-medium text-muted-foreground">待分析</span>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-yellow-600">{stats?.pendingAnalysis ?? 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <span className="text-sm font-medium text-muted-foreground">轉換率</span>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {((stats?.conversionRate ?? 0) * 100).toFixed(1)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* MEDDIC Score and Trend */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <h3 className="font-semibold">MEDDIC 分數趨勢</h3>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends?.data ?? []}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value) => new Date(value).toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' })}
                    className="text-xs"
                  />
                  <YAxis domain={[0, 100]} className="text-xs" />
                  <Tooltip
                    labelFormatter={(value) => new Date(value).toLocaleDateString('zh-TW')}
                    formatter={(value: number) => [value, 'MEDDIC 分數']}
                  />
                  <Line
                    type="monotone"
                    dataKey="avgMeddicScore"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h3 className="font-semibold">平均 MEDDIC 分數</h3>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center py-4">
            <ScoreGauge score={stats?.avgMeddicScore ?? 0} size="lg" />
            <div className="mt-4 flex items-center gap-2">
              {stats?.recentTrend === 'improving' && (
                <Badge variant="success">上升趨勢</Badge>
              )}
              {stats?.recentTrend === 'declining' && (
                <Badge variant="destructive">下降趨勢</Badge>
              )}
              {stats?.recentTrend === 'stable' && (
                <Badge variant="secondary">持平</Badge>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Conversations and Top Performers */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <h3 className="font-semibold">最近對話</h3>
            <Link to="/conversations" className="text-sm text-primary hover:underline">
              查看全部
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {conversations?.items.slice(0, 5).map((conv: Conversation) => (
                <Link
                  key={conv.id}
                  to="/conversations/$id"
                  params={{ id: conv.id }}
                  className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-accent"
                >
                  <div>
                    <div className="font-medium">{conv.salesRepName}</div>
                    <div className="text-sm text-muted-foreground">
                      {new Date(conv.createdAt).toLocaleString('zh-TW')}
                    </div>
                  </div>
                  <StatusBadge status={conv.status} />
                </Link>
              ))}
              {(!conversations?.items || conversations.items.length === 0) && (
                <div className="py-4 text-center text-muted-foreground">
                  尚無對話記錄
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h3 className="font-semibold">頂尖業務員</h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats?.topPerformers.map((performer: PerformerStats, index: number) => (
                <div
                  key={performer.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
                      {index + 1}
                    </div>
                    <div>
                      <div className="font-medium">{performer.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {performer.conversationCount} 通對話
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <ScoreGauge score={performer.avgMeddicScore} size="sm" showLabel={false} />
                    {performer.trend === 'up' && (
                      <span className="text-green-600">↑</span>
                    )}
                    {performer.trend === 'down' && (
                      <span className="text-red-600">↓</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
