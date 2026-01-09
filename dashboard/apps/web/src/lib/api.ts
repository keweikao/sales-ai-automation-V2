import type {
  DashboardStats,
  ConversationListResponse,
  ConversationDetail,
  ConversationFilters,
  WeeklyReportSummary,
  AnalyticsTrends,
  TrendPeriod,
  // Phase 4 types
  RepPerformanceDetail,
  TeamStats,
  CustomerHealth,
  RenewalPrediction,
  UpsellOpportunity,
  OnboardingChecklist,
  HandoffDocument,
  SystemHealth,
} from '@sales-ai/types';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export const api = {
  // ============================================
  // Dashboard & Analytics
  // ============================================
  getDashboardStats: () => fetchApi<DashboardStats>('/analytics/dashboard'),

  getWeeklyReport: (weekStart?: string) => {
    const params = weekStart ? `?week_start=${weekStart}` : '';
    return fetchApi<WeeklyReportSummary>(`/analytics/weekly-report${params}`);
  },

  getTrends: (period: TrendPeriod = '7d') =>
    fetchApi<AnalyticsTrends>(`/analytics/trends?period=${period}`),

  // Phase 4: Rep Performance
  getRepPerformance: (repId: string) =>
    fetchApi<RepPerformanceDetail>(`/analytics/rep/${repId}/details`),

  getTeamStats: () => fetchApi<TeamStats>('/analytics/team'),

  // ============================================
  // Conversations
  // ============================================
  getConversations: (filters?: ConversationFilters) => {
    const params = new URLSearchParams();
    if (filters?.status) params.set('status', filters.status);
    if (filters?.salesRep) params.set('sales_rep', filters.salesRep);
    if (filters?.startDate) params.set('start_date', filters.startDate);
    if (filters?.endDate) params.set('end_date', filters.endDate);
    if (filters?.limit) params.set('limit', filters.limit.toString());
    if (filters?.offset) params.set('offset', filters.offset.toString());
    const query = params.toString();
    return fetchApi<ConversationListResponse>(`/conversations${query ? `?${query}` : ''}`);
  },

  getConversation: (id: string) => fetchApi<ConversationDetail>(`/conversations/${id}`),

  // ============================================
  // Phase 4: Customer Success
  // ============================================
  getCustomerHealth: (customerId: string) =>
    fetchApi<CustomerHealth>(`/customers/${customerId}/health`),

  getAtRiskCustomers: (threshold: number = 50) =>
    fetchApi<{ customers: CustomerHealth[] }>(`/customers/at-risk?threshold=${threshold}`),

  getRenewalPrediction: (customerId: string) =>
    fetchApi<RenewalPrediction>(`/customers/${customerId}/renewal-prediction`),

  getUpsellOpportunities: (limit: number = 10) =>
    fetchApi<{ opportunities: UpsellOpportunity[] }>(`/customers/upsell-opportunities?limit=${limit}`),

  // ============================================
  // Phase 4: Deal Onboarding
  // ============================================
  createOnboardingChecklist: (data: { dealId: string; customerName: string; salesRepId: string }) =>
    fetchApi<OnboardingChecklist>('/onboarding/checklist', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getOnboardingChecklist: (dealId: string) =>
    fetchApi<OnboardingChecklist>(`/onboarding/checklist/${dealId}`),

  updateChecklistItem: (dealId: string, itemId: string, data: { status: string; notes?: string }) =>
    fetchApi<OnboardingChecklist>(`/onboarding/checklist/${dealId}/items/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  createHandoff: (data: { dealId: string; salesRepId: string; csRepId: string }) =>
    fetchApi<HandoffDocument>('/onboarding/handoff', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // ============================================
  // Phase 4: System Health (Ops)
  // ============================================
  getSystemHealth: () => fetchApi<SystemHealth>('/health/services'),
};
