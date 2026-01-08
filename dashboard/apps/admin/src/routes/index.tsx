import { createFileRoute } from '@tanstack/react-router';
import { Card, CardHeader, CardContent, Badge } from '@sales-ai/ui';

export const Route = createFileRoute('/')({
  component: AdminDashboard,
});

const systemStatus = {
  apiGateway: { status: 'healthy', latency: '45ms' },
  transcription: { status: 'healthy', latency: '120ms' },
  analysis: { status: 'healthy', latency: '850ms' },
  notification: { status: 'healthy', latency: '30ms' },
  scheduler: { status: 'healthy', latency: '15ms' },
};

const recentActivity = [
  { time: '10:30', action: 'Analysis completed', target: 'conv-001', user: 'system' },
  { time: '10:25', action: 'Transcription started', target: 'conv-002', user: 'system' },
  { time: '10:20', action: 'Slack notification sent', target: 'weekly-report', user: 'scheduler' },
  { time: '10:15', action: 'Agent config updated', target: 'agent-03', user: 'admin' },
];

function AdminDashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">系統總覽</h1>
        <p className="text-muted-foreground">監控系統健康狀態和活動</p>
      </div>

      {/* System Status */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {Object.entries(systemStatus).map(([name, info]) => (
          <Card key={name}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium capitalize">
                    {name.replace(/([A-Z])/g, ' $1').trim()}
                  </div>
                  <div className="text-xs text-muted-foreground">{info.latency}</div>
                </div>
                <Badge variant={info.status === 'healthy' ? 'success' : 'destructive'}>
                  {info.status === 'healthy' ? '正常' : '異常'}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Stats and Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <h3 className="font-semibold">系統指標</h3>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-muted-foreground">今日 API 請求</span>
              <span className="font-medium">12,453</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">平均響應時間</span>
              <span className="font-medium">156ms</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">錯誤率</span>
              <span className="font-medium text-green-600">0.02%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">活躍使用者</span>
              <span className="font-medium">24</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h3 className="font-semibold">最近活動</h3>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentActivity.map((activity, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between text-sm"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-muted-foreground">{activity.time}</span>
                    <span>{activity.action}</span>
                  </div>
                  <span className="text-muted-foreground">{activity.user}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
