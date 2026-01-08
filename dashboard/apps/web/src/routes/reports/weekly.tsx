import { createFileRoute } from '@tanstack/react-router';
import { useState } from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  ScoreGauge,
  Badge,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Input,
} from '@sales-ai/ui';
import { useWeeklyReport } from '@/hooks/use-dashboard';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export const Route = createFileRoute('/reports/weekly')({
  component: WeeklyReportPage,
});

function WeeklyReportPage() {
  const [weekStart, setWeekStart] = useState<string | undefined>();
  const { data: report, isLoading } = useWeeklyReport(weekStart);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-muted-foreground">載入中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">週報</h1>
          <p className="text-muted-foreground">銷售團隊表現分析</p>
        </div>
        <Input
          type="date"
          className="w-40"
          value={weekStart || ''}
          onChange={(e) => setWeekStart(e.target.value || undefined)}
        />
      </div>

      {report && (
        <>
          {/* Period Info */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-muted-foreground">報告期間</div>
                  <div className="text-lg font-medium">
                    {new Date(report.periodStart).toLocaleDateString('zh-TW')} -{' '}
                    {new Date(report.periodEnd).toLocaleDateString('zh-TW')}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-muted-foreground">產生時間</div>
                  <div className="text-sm">
                    {new Date(report.generatedAt).toLocaleString('zh-TW')}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Summary Stats */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <span className="text-sm font-medium text-muted-foreground">總對話數</span>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{report.totalConversations}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <span className="text-sm font-medium text-muted-foreground">已分析</span>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-green-600">{report.totalAnalyzed}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <span className="text-sm font-medium text-muted-foreground">分析率</span>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {((report.totalAnalyzed / report.totalConversations) * 100).toFixed(0)}%
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <span className="text-sm font-medium text-muted-foreground">平均 MEDDIC</span>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <ScoreGauge score={report.avgMeddicScore} size="sm" showLabel={false} />
                  <span className="text-2xl font-bold">{report.avgMeddicScore}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Rep Performance Chart and Table */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <h3 className="font-semibold">業務員 MEDDIC 分數比較</h3>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={report.byRep} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis type="number" domain={[0, 100]} />
                      <YAxis dataKey="name" type="category" width={80} />
                      <Tooltip formatter={(value: number) => [value, 'MEDDIC 分數']} />
                      <Bar dataKey="avgMeddicScore" fill="hsl(var(--primary))" radius={4} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h3 className="font-semibold">業務員表現排名</h3>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>排名</TableHead>
                      <TableHead>業務員</TableHead>
                      <TableHead>對話數</TableHead>
                      <TableHead>分數</TableHead>
                      <TableHead>趨勢</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {report.byRep.map((rep, index) => (
                      <TableRow key={rep.id}>
                        <TableCell>
                          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                            {index + 1}
                          </div>
                        </TableCell>
                        <TableCell className="font-medium">{rep.name}</TableCell>
                        <TableCell>{rep.conversationCount}</TableCell>
                        <TableCell>
                          <span
                            className={
                              rep.avgMeddicScore >= 70
                                ? 'text-green-600'
                                : rep.avgMeddicScore >= 50
                                  ? 'text-yellow-600'
                                  : 'text-red-600'
                            }
                          >
                            {rep.avgMeddicScore}
                          </span>
                        </TableCell>
                        <TableCell>
                          {rep.trend === 'up' && <Badge variant="success">↑ 上升</Badge>}
                          {rep.trend === 'down' && <Badge variant="destructive">↓ 下降</Badge>}
                          {rep.trend === 'stable' && <Badge variant="secondary">→ 持平</Badge>}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>

          {/* Insights */}
          <Card>
            <CardHeader>
              <h3 className="font-semibold">本週洞察</h3>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {report.insights.map((insight, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-3 rounded-lg border p-3"
                  >
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      {index + 1}
                    </div>
                    <span className="text-sm">{insight}</span>
                  </li>
                ))}
                {report.insights.length === 0 && (
                  <li className="text-center text-muted-foreground py-4">
                    本週尚無洞察資料
                  </li>
                )}
              </ul>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
