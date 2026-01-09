import { createFileRoute, Link } from '@tanstack/react-router';
import {
  Card,
  CardHeader,
  CardContent,
  StatusBadge,
  ScoreGauge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  MEDDICCard,
  CoachingPanel,
  TranscriptViewer,
  Button,
  Badge,
} from '@sales-ai/ui';
import { useConversation } from '@/hooks/use-dashboard';

export const Route = createFileRoute('/conversations/$id')({
  component: ConversationDetailPage,
});

function ConversationDetailPage() {
  const { id } = Route.useParams();
  const { data: conversation, isLoading, error } = useConversation(id);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-muted-foreground">載入中...</div>
      </div>
    );
  }

  if (error || !conversation) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="text-muted-foreground mb-4">無法載入對話詳情</div>
        <Link to="/conversations" className="text-primary hover:underline">
          返回列表
        </Link>
      </div>
    );
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins} 分 ${secs} 秒`;
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Link to="/conversations" className="text-muted-foreground hover:text-foreground">
              ← 返回列表
            </Link>
          </div>
          <h1 className="text-2xl font-bold">對話詳情</h1>
          <p className="text-muted-foreground font-mono">{conversation.id}</p>
        </div>
        <StatusBadge status={conversation.status} />
      </div>

      {/* Basic Info */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-4">
            <div>
              <div className="text-sm text-muted-foreground">業務員</div>
              <div className="font-medium">{conversation.salesRepName || '-'}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">對話類型</div>
              <div className="font-medium capitalize">{conversation.conversationType || '-'}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">通話時長</div>
              <div className="font-medium">{formatDuration(conversation.audioDurationSeconds)}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">建立時間</div>
              <div className="font-medium">
                {new Date(conversation.createdAt).toLocaleString('zh-TW')}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Summary */}
      {conversation.analysis && (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <h3 className="font-semibold">分析摘要</h3>
            </CardHeader>
            <CardContent className="space-y-4">
              {conversation.analysis.summary && (
                <div>
                  <div className="text-sm font-medium text-muted-foreground mb-1">對話摘要</div>
                  <p className="text-sm">{conversation.analysis.summary}</p>
                </div>
              )}
              {conversation.analysis.customerSummary && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-sm font-medium text-muted-foreground">客戶摘要</div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(conversation.analysis?.customerSummary || '')}
                    >
                      複製
                    </Button>
                  </div>
                  <p className="text-sm bg-accent/50 rounded-lg p-3">
                    {conversation.analysis.customerSummary}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <h3 className="font-semibold">MEDDIC 分數</h3>
            </CardHeader>
            <CardContent className="flex justify-center py-4">
              <ScoreGauge
                score={conversation.analysis.meddicScore ?? 0}
                size="lg"
              />
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs for detailed content */}
      <Tabs defaultValue="transcript">
        <TabsList>
          <TabsTrigger value="transcript">逐字稿</TabsTrigger>
          <TabsTrigger value="meddic">MEDDIC 分析</TabsTrigger>
          <TabsTrigger value="coaching">銷售指導</TabsTrigger>
          <TabsTrigger value="buyer">買家洞察</TabsTrigger>
        </TabsList>

        <TabsContent value="transcript">
          <Card>
            <CardHeader>
              <h3 className="font-semibold">逐字稿</h3>
              {conversation.transcript && (
                <div className="text-sm text-muted-foreground">
                  {conversation.transcript.language} · {formatDuration(conversation.transcript.durationSeconds)}
                </div>
              )}
            </CardHeader>
            <CardContent>
              {conversation.transcript?.segments ? (
                <TranscriptViewer
                  segments={conversation.transcript.segments}
                  className="max-h-[600px]"
                />
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  尚無逐字稿內容
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="meddic">
          {conversation.analysis?.buyerData?.meddic ? (
            <MEDDICCard data={conversation.analysis.buyerData.meddic} />
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                尚無 MEDDIC 分析資料
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="coaching">
          {conversation.analysis?.sellerCoaching ? (
            <CoachingPanel coaching={conversation.analysis.sellerCoaching} />
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                尚無銷售指導資料
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="buyer">
          <Card>
            <CardHeader>
              <h3 className="font-semibold">買家洞察</h3>
            </CardHeader>
            <CardContent className="space-y-6">
              {conversation.analysis?.buyerData ? (
                <>
                  <div>
                    <div className="text-sm font-medium text-muted-foreground mb-2">已識別需求</div>
                    <div className="flex flex-wrap gap-2">
                      {conversation.analysis.buyerData.identifiedNeeds.map((need: string, i: number) => (
                        <Badge key={i} variant="secondary">{need}</Badge>
                      ))}
                      {conversation.analysis.buyerData.identifiedNeeds.length === 0 && (
                        <span className="text-sm text-muted-foreground">尚未識別</span>
                      )}
                    </div>
                  </div>

                  <div>
                    <div className="text-sm font-medium text-muted-foreground mb-2">痛點</div>
                    <div className="flex flex-wrap gap-2">
                      {conversation.analysis.buyerData.painPoints.map((pain: string, i: number) => (
                        <Badge key={i} variant="destructive">{pain}</Badge>
                      ))}
                      {conversation.analysis.buyerData.painPoints.length === 0 && (
                        <span className="text-sm text-muted-foreground">尚未識別</span>
                      )}
                    </div>
                  </div>

                  <div>
                    <div className="text-sm font-medium text-muted-foreground mb-2">猶豫點</div>
                    <div className="flex flex-wrap gap-2">
                      {conversation.analysis.buyerData.hesitations.map((hes: string, i: number) => (
                        <Badge key={i} variant="warning">{hes}</Badge>
                      ))}
                      {conversation.analysis.buyerData.hesitations.length === 0 && (
                        <span className="text-sm text-muted-foreground">尚未識別</span>
                      )}
                    </div>
                  </div>

                  {conversation.analysis.buyerData.trustScore !== undefined && (
                    <div>
                      <div className="text-sm font-medium text-muted-foreground mb-2">信任分數</div>
                      <div className="flex items-center gap-4">
                        <div className="h-2 flex-1 rounded-full bg-muted">
                          <div
                            className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${conversation.analysis.buyerData.trustScore}%` }}
                          />
                        </div>
                        <span className="font-medium">{conversation.analysis.buyerData.trustScore}%</span>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center text-muted-foreground py-4">
                  尚無買家洞察資料
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
