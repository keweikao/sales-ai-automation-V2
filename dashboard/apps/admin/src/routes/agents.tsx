import { createFileRoute } from '@tanstack/react-router';
import { Card, CardHeader, CardContent, Badge, Button } from '@sales-ai/ui';

export const Route = createFileRoute('/agents')({
  component: AgentsPage,
});

const agents = [
  {
    id: 'agent-01',
    name: 'Lead Source Agent',
    module: 'modules/01-lead-source',
    status: 'active',
    lastRun: '2026-01-08T10:00:00Z',
    version: '1.2.0',
    description: '處理來自各種來源的潛在客戶資料',
  },
  {
    id: 'agent-02',
    name: 'MQL Qualification Agent',
    module: 'modules/02-mql-qualification',
    status: 'active',
    lastRun: '2026-01-08T10:05:00Z',
    version: '1.1.0',
    description: '評估和資格審核行銷合格線索',
  },
  {
    id: 'agent-03',
    name: 'Sales Conversation Agent',
    module: 'modules/03-sales-conversation',
    status: 'active',
    lastRun: '2026-01-08T10:30:00Z',
    version: '2.0.0',
    description: '分析銷售對話並提供 MEDDIC 評分',
  },
  {
    id: 'agent-04',
    name: 'Deal Onboarding Agent',
    module: 'modules/04-deal-onboarding',
    status: 'active',
    lastRun: '2026-01-08T09:45:00Z',
    version: '1.0.0',
    description: '處理新客戶上線流程',
  },
  {
    id: 'agent-05',
    name: 'Customer Success Agent',
    module: 'modules/05-customer-success',
    status: 'active',
    lastRun: '2026-01-08T10:15:00Z',
    version: '1.0.0',
    description: '監控客戶成功指標',
  },
  {
    id: 'agent-06',
    name: 'Analytics Agent',
    module: 'modules/06-analytics',
    status: 'active',
    lastRun: '2026-01-08T10:00:00Z',
    version: '1.3.0',
    description: '生成分析報告和洞察',
  },
];

function AgentsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Agent 管理</h1>
          <p className="text-muted-foreground">管理和監控 AI Agent 狀態</p>
        </div>
        <Button>重新載入全部</Button>
      </div>

      <div className="grid gap-4">
        {agents.map((agent) => (
          <Card key={agent.id}>
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold">{agent.name}</h3>
                    <Badge variant={agent.status === 'active' ? 'success' : 'secondary'}>
                      {agent.status === 'active' ? '運行中' : '停止'}
                    </Badge>
                    <Badge variant="outline">v{agent.version}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{agent.description}</p>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2">
                    <span>模組: {agent.module}</span>
                    <span>最後執行: {new Date(agent.lastRun).toLocaleString('zh-TW')}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">查看日誌</Button>
                  <Button variant="outline" size="sm">配置</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Prompt Version Management */}
      <Card>
        <CardHeader>
          <h3 className="font-semibold">Prompt 版本管理</h3>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <div className="font-medium">MEDDIC Analysis Prompt</div>
                <div className="text-sm text-muted-foreground">用於 Sales Conversation Agent</div>
              </div>
              <div className="flex items-center gap-3">
                <Badge>v2.1.0</Badge>
                <Button variant="outline" size="sm">編輯</Button>
              </div>
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <div className="font-medium">Coaching Insights Prompt</div>
                <div className="text-sm text-muted-foreground">用於生成銷售指導建議</div>
              </div>
              <div className="flex items-center gap-3">
                <Badge>v1.5.0</Badge>
                <Button variant="outline" size="sm">編輯</Button>
              </div>
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <div className="font-medium">Lead Qualification Prompt</div>
                <div className="text-sm text-muted-foreground">用於 MQL 資格審核</div>
              </div>
              <div className="flex items-center gap-3">
                <Badge>v1.2.0</Badge>
                <Button variant="outline" size="sm">編輯</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
