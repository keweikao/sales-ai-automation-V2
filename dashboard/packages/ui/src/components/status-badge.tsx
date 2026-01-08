import * as React from 'react';
import { Badge } from './badge';
import { cn } from '../lib/utils';

export type ConversationStatus = 'pending' | 'transcribing' | 'analyzing' | 'completed' | 'failed';

export interface StatusBadgeProps {
  status: ConversationStatus;
  className?: string;
}

const statusConfig: Record<ConversationStatus, { label: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'destructive' }> = {
  pending: { label: '待處理', variant: 'secondary' },
  transcribing: { label: '轉錄中', variant: 'warning' },
  analyzing: { label: '分析中', variant: 'warning' },
  completed: { label: '已完成', variant: 'success' },
  failed: { label: '失敗', variant: 'destructive' },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.pending;

  return (
    <Badge variant={config.variant} className={cn(className)}>
      {config.label}
    </Badge>
  );
}
