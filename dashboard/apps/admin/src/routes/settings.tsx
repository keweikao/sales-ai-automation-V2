import { createFileRoute } from '@tanstack/react-router';
import { useState } from 'react';
import { Card, CardHeader, CardContent, Input, Button, Badge } from '@sales-ai/ui';

export const Route = createFileRoute('/settings')({
  component: SettingsPage,
});

function SettingsPage() {
  const [apiUrl, setApiUrl] = useState('https://api-gateway-xxx.asia-east1.run.app');
  const [slackWebhook, setSlackWebhook] = useState('https://hooks.slack.com/services/xxx');
  const [slackChannel, setSlackChannel] = useState('#sales-alerts');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">系統設定</h1>
        <p className="text-muted-foreground">配置 API 和整合設定</p>
      </div>

      {/* API Configuration */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">API 配置</h3>
            <Badge variant="success">已連接</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">API Gateway URL</label>
            <Input
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <label className="text-sm font-medium">GCP Project ID</label>
            <Input
              value="sales-ai-automation-v2"
              disabled
              className="mt-1 bg-muted"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Firestore Database</label>
            <Input
              value="(default)"
              disabled
              className="mt-1 bg-muted"
            />
          </div>
          <div className="pt-2">
            <Button>儲存變更</Button>
          </div>
        </CardContent>
      </Card>

      {/* Slack Integration */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Slack 整合</h3>
            <Badge variant="success">已啟用</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Webhook URL</label>
            <Input
              type="password"
              value={slackWebhook}
              onChange={(e) => setSlackWebhook(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <label className="text-sm font-medium">通知頻道</label>
            <Input
              value={slackChannel}
              onChange={(e) => setSlackChannel(e.target.value)}
              className="mt-1"
            />
          </div>
          <div className="flex gap-2 pt-2">
            <Button>儲存變更</Button>
            <Button variant="outline">測試連接</Button>
          </div>
        </CardContent>
      </Card>

      {/* Scheduler Settings */}
      <Card>
        <CardHeader>
          <h3 className="font-semibold">排程設定</h3>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">週報排程</div>
              <div className="text-sm text-muted-foreground">每週一 09:00 產生週報</div>
            </div>
            <Badge variant="success">啟用</Badge>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">即時通知</div>
              <div className="text-sm text-muted-foreground">對話完成時發送 Slack 通知</div>
            </div>
            <Badge variant="success">啟用</Badge>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Coach 警報</div>
              <div className="text-sm text-muted-foreground">MEDDIC 分數低於閾值時警報</div>
            </div>
            <Badge variant="secondary">停用</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
