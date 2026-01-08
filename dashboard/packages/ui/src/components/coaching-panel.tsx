import * as React from 'react';
import { Card, CardHeader, CardContent } from './card';
import { Badge } from './badge';
import { cn } from '../lib/utils';

export interface CoachingInsight {
  category: 'strength' | 'improvement' | 'action';
  content: string;
  priority?: 'high' | 'medium' | 'low';
}

export interface SellerCoaching {
  progressScore?: number;
  recommendedStrategy?: string;
  insights: CoachingInsight[];
  nextSteps: string[];
}

export interface CoachingPanelProps {
  coaching: SellerCoaching;
  className?: string;
}

const categoryConfig = {
  strength: {
    label: '優勢',
    icon: '💪',
    bgColor: 'bg-green-50 dark:bg-green-950',
    borderColor: 'border-l-green-500',
  },
  improvement: {
    label: '改進',
    icon: '📈',
    bgColor: 'bg-yellow-50 dark:bg-yellow-950',
    borderColor: 'border-l-yellow-500',
  },
  action: {
    label: '行動',
    icon: '🎯',
    bgColor: 'bg-blue-50 dark:bg-blue-950',
    borderColor: 'border-l-blue-500',
  },
};

const priorityVariant: Record<string, 'destructive' | 'warning' | 'secondary'> = {
  high: 'destructive',
  medium: 'warning',
  low: 'secondary',
};

function InsightItem({ insight }: { insight: CoachingInsight }) {
  const config = categoryConfig[insight.category];

  return (
    <div
      className={cn(
        'rounded-r-lg border-l-4 p-3',
        config.bgColor,
        config.borderColor
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <span>{config.icon}</span>
        <span className="text-sm font-medium">{config.label}</span>
        {insight.priority && (
          <Badge variant={priorityVariant[insight.priority]} className="ml-auto">
            {insight.priority === 'high' ? '高' : insight.priority === 'medium' ? '中' : '低'}
          </Badge>
        )}
      </div>
      <p className="text-sm text-muted-foreground">{insight.content}</p>
    </div>
  );
}

export function CoachingPanel({ coaching, className }: CoachingPanelProps) {
  const groupedInsights = {
    strength: coaching.insights.filter((i) => i.category === 'strength'),
    improvement: coaching.insights.filter((i) => i.category === 'improvement'),
    action: coaching.insights.filter((i) => i.category === 'action'),
  };

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">銷售指導</h3>
          {coaching.progressScore !== undefined && (
            <Badge variant="outline">
              進度: {coaching.progressScore}%
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {coaching.recommendedStrategy && (
          <div className="rounded-lg bg-muted p-3">
            <div className="text-sm font-medium mb-1">建議策略</div>
            <p className="text-sm text-muted-foreground">{coaching.recommendedStrategy}</p>
          </div>
        )}

        {coaching.insights.length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-medium">洞察</div>
            <div className="space-y-2">
              {coaching.insights.map((insight, index) => (
                <InsightItem key={index} insight={insight} />
              ))}
            </div>
          </div>
        )}

        {coaching.nextSteps.length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-medium">下一步行動</div>
            <ul className="space-y-1">
              {coaching.nextSteps.map((step, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="text-primary">•</span>
                  {step}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
