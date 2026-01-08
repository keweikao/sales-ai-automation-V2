// ============================================
// Sales AI Dashboard - Shared Types
// ============================================

// ----- User & Auth -----
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'manager' | 'sales';
}

// ----- Pagination -----
export interface PaginationParams {
  page: number;
  limit: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

// ----- Conversation Types -----
export type ConversationStatus =
  | 'pending'
  | 'transcribing'
  | 'analyzing'
  | 'completed'
  | 'failed';

export type ConversationType =
  | 'discovery'
  | 'demo'
  | 'negotiation'
  | 'follow_up'
  | 'closing';

export interface Conversation {
  id: string;
  leadId?: string;
  salesRepName?: string;
  status: ConversationStatus;
  conversationType?: ConversationType;
  createdAt: string; // ISO datetime
  completedAt?: string;
}

export interface ConversationListResponse {
  items: Conversation[];
  total: number;
  limit: number;
  offset: number;
}

export interface ConversationFilters {
  status?: ConversationStatus;
  salesRep?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  offset?: number;
}

// ----- Transcript Types -----
export interface TranscriptSegment {
  speaker?: string;
  text: string;
  start?: number; // seconds
  end?: number;
}

export interface Transcript {
  segments: TranscriptSegment[];
  fullText?: string;
  language: string;
  durationSeconds?: number;
}

// ----- MEDDIC Types -----
export interface MEDDICData {
  metrics?: string;
  economicBuyer?: string;
  decisionCriteria?: string;
  decisionProcess?: string;
  identifyPain?: string;
  champion?: string;
}

export type MEDDICElement = keyof MEDDICData;

export const MEDDIC_LABELS: Record<MEDDICElement, string> = {
  metrics: 'Metrics',
  economicBuyer: 'Economic Buyer',
  decisionCriteria: 'Decision Criteria',
  decisionProcess: 'Decision Process',
  identifyPain: 'Identify Pain',
  champion: 'Champion',
};

// ----- Buyer Data Types -----
export interface BuyerData {
  identifiedNeeds: string[];
  hesitations: string[];
  painPoints: string[];
  trustScore?: number; // 0-100
  meddic?: MEDDICData;
}

// ----- Coaching Types -----
export type InsightCategory = 'strength' | 'improvement' | 'action';
export type InsightPriority = 'high' | 'medium' | 'low';

export interface CoachingInsight {
  category: InsightCategory;
  content: string;
  priority?: InsightPriority;
}

export interface SellerCoaching {
  progressScore?: number; // 0-100
  recommendedStrategy?: string;
  insights: CoachingInsight[];
  nextSteps: string[];
}

// ----- Analysis Result Types -----
export interface AnalysisResult {
  contextData?: Record<string, unknown>;
  buyerData?: BuyerData;
  sellerCoaching?: SellerCoaching;
  meddicScore?: number; // 0-100
  summary?: string;
  customerSummary?: string;
  analyzedAt?: string;
}

// ----- Conversation Detail (Full) -----
export interface ConversationDetail extends Conversation {
  transcript?: Transcript;
  analysis?: AnalysisResult;
  audioFileUri?: string;
  audioDurationSeconds?: number;
}

// ----- Analytics Types -----
export type TrendDirection = 'up' | 'down' | 'stable';
export type OverallTrend = 'improving' | 'declining' | 'stable';
export type TrendPeriod = '7d' | '30d' | '90d';

export interface PerformerStats {
  id: string;
  name: string;
  conversationCount: number;
  avgMeddicScore: number;
  trend?: TrendDirection;
}

export interface DashboardStats {
  totalConversations: number;
  completedToday: number;
  pendingAnalysis: number;
  avgMeddicScore: number;
  conversionRate: number;
  topPerformers: PerformerStats[];
  recentTrend?: OverallTrend;
  lastUpdated: string;
}

export interface WeeklyReportSummary {
  periodStart: string;
  periodEnd: string;
  totalConversations: number;
  totalAnalyzed: number;
  avgMeddicScore: number;
  byRep: PerformerStats[];
  insights: string[];
  generatedAt: string;
}

export interface TrendData {
  date: string;
  conversationCount: number;
  avgMeddicScore: number;
}

export interface AnalyticsTrends {
  period: TrendPeriod;
  data: TrendData[];
  overallTrend: OverallTrend;
}

// ----- API Response Helpers -----
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
}

// ----- Status Helpers -----
export const STATUS_CONFIG: Record<
  ConversationStatus,
  { label: string; color: string }
> = {
  pending: { label: '待處理', color: 'yellow' },
  transcribing: { label: '轉錄中', color: 'blue' },
  analyzing: { label: '分析中', color: 'purple' },
  completed: { label: '已完成', color: 'green' },
  failed: { label: '失敗', color: 'red' },
};

export const CONVERSATION_TYPE_CONFIG: Record<
  ConversationType,
  { label: string; color: string }
> = {
  discovery: { label: '發現', color: 'blue' },
  demo: { label: '演示', color: 'purple' },
  negotiation: { label: '談判', color: 'orange' },
  follow_up: { label: '跟進', color: 'gray' },
  closing: { label: '成交', color: 'green' },
};

// ============================================
// Phase 4: Customer Success Types
// ============================================

export type HealthLevel = 'healthy' | 'at_risk' | 'critical';
export type RenewalProbability = 'high' | 'medium' | 'low';

export interface CustomerHealth {
  customerId: string;
  customerName: string;
  healthScore: number; // 0-100
  healthLevel: HealthLevel;

  // Score factors
  engagementScore: number;
  sentimentScore: number;
  usageScore: number;
  supportScore: number;

  // Risk indicators
  riskFactors: string[];
  improvementActions: string[];

  lastCheckIn?: string;
  nextCheckInDue?: string;
  calculatedAt: string;
}

export interface RenewalPrediction {
  customerId: string;
  contractEndDate: string;
  daysUntilRenewal: number;
  renewalProbability: RenewalProbability;
  confidence: number; // 0-1

  positiveFactors: string[];
  negativeFactors: string[];
  recommendedActions: string[];

  predictedAt: string;
}

export interface UpsellOpportunity {
  customerId: string;
  opportunityType: string; // e.g., "seat_expansion", "feature_upgrade"
  confidence: number; // 0-1
  estimatedValue?: number;

  signals: string[];
  recommendedApproach: string;
  bestTiming?: string;

  detectedAt: string;
}

export const HEALTH_LEVEL_CONFIG: Record<
  HealthLevel,
  { label: string; color: string; minScore: number }
> = {
  healthy: { label: '健康', color: 'green', minScore: 80 },
  at_risk: { label: '風險', color: 'yellow', minScore: 50 },
  critical: { label: '危急', color: 'red', minScore: 0 },
};

export const RENEWAL_PROBABILITY_CONFIG: Record<
  RenewalProbability,
  { label: string; color: string }
> = {
  high: { label: '高', color: 'green' },
  medium: { label: '中', color: 'yellow' },
  low: { label: '低', color: 'red' },
};

// ============================================
// Phase 4: Deal Onboarding Types
// ============================================

export type OnboardingStatus = 'not_started' | 'in_progress' | 'completed' | 'blocked';

export interface ChecklistItem {
  id: string;
  title: string;
  description?: string;
  required: boolean;
  status: OnboardingStatus;
  completedAt?: string;
  completedBy?: string;
  notes?: string;
}

export interface OnboardingChecklist {
  dealId: string;
  customerName: string;
  salesRepId: string;
  csRepId?: string;
  items: ChecklistItem[];
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  overallStatus: OnboardingStatus;
}

export interface HandoffDocument {
  dealId: string;
  fromRep: string; // Sales
  toRep: string; // Customer Success
  customerSummary: string;
  keyPainPoints: string[];
  identifiedNeeds: string[];
  championInfo?: string;
  decisionProcess?: string;
  specialNotes?: string;
  handoffDate: string;
}

export const ONBOARDING_STATUS_CONFIG: Record<
  OnboardingStatus,
  { label: string; color: string }
> = {
  not_started: { label: '未開始', color: 'gray' },
  in_progress: { label: '進行中', color: 'blue' },
  completed: { label: '已完成', color: 'green' },
  blocked: { label: '受阻', color: 'red' },
};

// ============================================
// Phase 4: Rep Performance Types (Extended)
// ============================================

export interface RepPerformanceDetail extends PerformerStats {
  strengths: string[];
  improvementAreas: string[];
  comparisonToTeam: number; // percentile 0-100
  recentConversations: Conversation[];
  meddicBreakdown: {
    metrics: number;
    economicBuyer: number;
    decisionCriteria: number;
    decisionProcess: number;
    identifyPain: number;
    champion: number;
  };
}

export interface TeamStats {
  totalReps: number;
  activeReps: number;
  totalConversations: number;
  avgMeddicScore: number;
  topPerformerId: string;
  bottomPerformerId: string;
  teamTrend: OverallTrend;
  periodStart: string;
  periodEnd: string;
}

// ============================================
// Phase 4: System Health Types (Ops)
// ============================================

export type ServiceStatus = 'healthy' | 'degraded' | 'unhealthy';

export interface ServiceHealth {
  name: string;
  status: ServiceStatus;
  latency?: number; // ms
  lastChecked: string;
  errorMessage?: string;
}

export interface SystemHealth {
  overall: ServiceStatus;
  services: ServiceHealth[];
  checkedAt: string;
}

export const SERVICE_STATUS_CONFIG: Record<
  ServiceStatus,
  { label: string; color: string }
> = {
  healthy: { label: '正常', color: 'green' },
  degraded: { label: '降級', color: 'yellow' },
  unhealthy: { label: '異常', color: 'red' },
};
