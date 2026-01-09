import type {
  DashboardStats,
  ConversationListResponse,
  ConversationDetail,
  WeeklyReportSummary,
  AnalyticsTrends,
  Conversation,
} from '@sales-ai/types';

export const mockDashboardStats: DashboardStats = {
  totalConversations: 156,
  completedToday: 12,
  pendingAnalysis: 3,
  avgMeddicScore: 72,
  conversionRate: 0.34,
  topPerformers: [
    { id: '1', name: '張小明', conversationCount: 28, avgMeddicScore: 85, trend: 'up' },
    { id: '2', name: '李美華', conversationCount: 24, avgMeddicScore: 78, trend: 'stable' },
    { id: '3', name: '王大偉', conversationCount: 22, avgMeddicScore: 74, trend: 'up' },
  ],
  recentTrend: 'improving',
  lastUpdated: new Date().toISOString(),
};

const mockConversations: Conversation[] = [
  {
    id: 'conv-001',
    leadId: 'lead-001',
    salesRepName: '張小明',
    status: 'completed',
    conversationType: 'discovery',
    createdAt: '2026-01-08T09:00:00Z',
    completedAt: '2026-01-08T09:45:00Z',
  },
  {
    id: 'conv-002',
    leadId: 'lead-002',
    salesRepName: '李美華',
    status: 'analyzing',
    conversationType: 'demo',
    createdAt: '2026-01-08T10:30:00Z',
  },
  {
    id: 'conv-003',
    leadId: 'lead-003',
    salesRepName: '王大偉',
    status: 'completed',
    conversationType: 'negotiation',
    createdAt: '2026-01-08T11:00:00Z',
    completedAt: '2026-01-08T11:50:00Z',
  },
  {
    id: 'conv-004',
    leadId: 'lead-004',
    salesRepName: '張小明',
    status: 'pending',
    conversationType: 'follow_up',
    createdAt: '2026-01-08T14:00:00Z',
  },
  {
    id: 'conv-005',
    leadId: 'lead-005',
    salesRepName: '李美華',
    status: 'failed',
    conversationType: 'closing',
    createdAt: '2026-01-07T16:00:00Z',
  },
];

export const mockConversationList: ConversationListResponse = {
  items: mockConversations,
  total: 156,
  limit: 20,
  offset: 0,
};

export const mockConversationDetail: ConversationDetail = {
  id: 'conv-001',
  leadId: 'lead-001',
  salesRepName: '張小明',
  status: 'completed',
  conversationType: 'discovery',
  createdAt: '2026-01-08T09:00:00Z',
  completedAt: '2026-01-08T09:45:00Z',
  audioDurationSeconds: 2700,
  transcript: {
    segments: [
      { speaker: '張小明', text: '您好，感謝您今天撥空與我們通話。', start: 0, end: 5 },
      { speaker: '客戶', text: '不客氣，我們對你們的產品很感興趣。', start: 5, end: 10 },
      { speaker: '張小明', text: '太好了！能否先分享一下您目前遇到的主要挑戰是什麼？', start: 10, end: 18 },
      { speaker: '客戶', text: '我們目前的銷售流程效率很低，很多時間都花在行政工作上。', start: 18, end: 28 },
      { speaker: '張小明', text: '我理解。能否具體說明一下，這個問題對您的業績影響有多大？', start: 28, end: 38 },
      { speaker: '客戶', text: '大概影響了 30% 的銷售效率，每個月損失約 50 萬的潛在營收。', start: 38, end: 50 },
    ],
    fullText: '',
    language: 'zh-TW',
    durationSeconds: 2700,
  },
  analysis: {
    meddicScore: 78,
    summary: '這是一次成功的發現階段對話，成功識別了客戶的核心痛點和量化指標。',
    customerSummary: '客戶是一家中型製造業公司，面臨銷售效率低下的問題，每月損失約 50 萬潛在營收。對自動化解決方案有高度興趣。',
    buyerData: {
      identifiedNeeds: ['提升銷售效率', '減少行政工作時間', '增加營收'],
      hesitations: ['預算審批流程', '現有系統整合'],
      painPoints: ['銷售流程效率低', '30% 效率損失', '每月 50 萬潛在營收損失'],
      trustScore: 75,
      meddic: {
        metrics: '每月損失約 50 萬潛在營收，效率損失 30%',
        economicBuyer: '財務長 陳先生',
        decisionCriteria: 'ROI、整合性、易用性',
        decisionProcess: '需經過 IT 評估、財務審批、CEO 最終決定',
        identifyPain: '銷售流程效率低，大量時間花在行政工作',
        champion: '銷售經理 林小姐',
      },
    },
    sellerCoaching: {
      progressScore: 72,
      recommendedStrategy: '建議在下次會議中邀請財務長參與，並準備詳細的 ROI 分析報告。',
      insights: [
        { category: 'strength', content: '成功建立信任並識別核心痛點', priority: 'high' },
        { category: 'strength', content: '獲取了具體的量化指標', priority: 'medium' },
        { category: 'improvement', content: '可以更深入了解決策流程的時間表', priority: 'high' },
        { category: 'action', content: '準備客製化的 ROI 分析', priority: 'high' },
      ],
      nextSteps: [
        '準備詳細的 ROI 分析報告',
        '安排與財務長的會議',
        '提供產品試用帳號',
        '準備客戶成功案例分享',
      ],
    },
    analyzedAt: '2026-01-08T09:50:00Z',
  },
};

export const mockWeeklyReport: WeeklyReportSummary = {
  periodStart: '2026-01-01',
  periodEnd: '2026-01-07',
  totalConversations: 45,
  totalAnalyzed: 42,
  avgMeddicScore: 68,
  byRep: [
    { id: '1', name: '張小明', conversationCount: 15, avgMeddicScore: 75, trend: 'up' },
    { id: '2', name: '李美華', conversationCount: 12, avgMeddicScore: 70, trend: 'stable' },
    { id: '3', name: '王大偉', conversationCount: 10, avgMeddicScore: 65, trend: 'down' },
    { id: '4', name: '陳小芳', conversationCount: 8, avgMeddicScore: 62, trend: 'up' },
  ],
  insights: [
    '本週整體 MEDDIC 分數較上週提升 5%',
    '張小明在識別經濟決策者方面表現優異',
    '建議加強團隊在決策流程探詢的技巧',
    '本週發現階段的對話品質明顯提升',
  ],
  generatedAt: '2026-01-08T00:00:00Z',
};

export const mockTrends: AnalyticsTrends = {
  period: '7d',
  data: [
    { date: '2026-01-02', conversationCount: 18, avgMeddicScore: 65 },
    { date: '2026-01-03', conversationCount: 22, avgMeddicScore: 68 },
    { date: '2026-01-04', conversationCount: 15, avgMeddicScore: 70 },
    { date: '2026-01-05', conversationCount: 20, avgMeddicScore: 72 },
    { date: '2026-01-06', conversationCount: 25, avgMeddicScore: 69 },
    { date: '2026-01-07', conversationCount: 28, avgMeddicScore: 74 },
    { date: '2026-01-08', conversationCount: 12, avgMeddicScore: 76 },
  ],
  overallTrend: 'improving',
};
