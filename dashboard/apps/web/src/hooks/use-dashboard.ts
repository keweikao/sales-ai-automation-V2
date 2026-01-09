import { useQuery } from '@tanstack/react-query';
import type { TrendPeriod, ConversationFilters } from '@sales-ai/types';
import { api } from '../lib/api';
import {
  mockDashboardStats,
  mockConversationList,
  mockConversationDetail,
  mockWeeklyReport,
  mockTrends,
} from '../lib/mock-data';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => {
      if (USE_MOCK) return mockDashboardStats;
      return api.getDashboardStats();
    },
  });
}

export function useConversations(filters?: ConversationFilters) {
  return useQuery({
    queryKey: ['conversations', filters],
    queryFn: async () => {
      if (USE_MOCK) return mockConversationList;
      return api.getConversations(filters);
    },
  });
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: ['conversation', id],
    queryFn: async () => {
      if (USE_MOCK) return mockConversationDetail;
      return api.getConversation(id);
    },
    enabled: !!id,
  });
}

export function useWeeklyReport(weekStart?: string) {
  return useQuery({
    queryKey: ['weekly-report', weekStart],
    queryFn: async () => {
      if (USE_MOCK) return mockWeeklyReport;
      return api.getWeeklyReport(weekStart);
    },
  });
}

export function useTrends(period: TrendPeriod = '7d') {
  return useQuery({
    queryKey: ['trends', period],
    queryFn: async () => {
      if (USE_MOCK) return mockTrends;
      return api.getTrends(period);
    },
  });
}
