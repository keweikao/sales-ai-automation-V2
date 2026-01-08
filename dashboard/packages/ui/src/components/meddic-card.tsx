import * as React from 'react';
import { Card, CardHeader, CardContent } from './card';
import { cn } from '../lib/utils';

export interface MEDDICData {
  metrics?: string;
  economicBuyer?: string;
  decisionCriteria?: string;
  decisionProcess?: string;
  identifyPain?: string;
  champion?: string;
}

export interface MEDDICCardProps {
  data: MEDDICData;
  className?: string;
}

interface MEDDICItemProps {
  label: string;
  abbr: string;
  value?: string;
  color: string;
}

function MEDDICItem({ label, abbr, value, color }: MEDDICItemProps) {
  const hasValue = Boolean(value && value.trim());

  return (
    <div className="flex items-start gap-3 py-2">
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white',
          hasValue ? color : 'bg-gray-300 dark:bg-gray-600'
        )}
      >
        {abbr}
      </div>
      <div className="flex-1">
        <div className="text-sm font-medium text-foreground">{label}</div>
        <div className={cn(
          'text-sm',
          hasValue ? 'text-muted-foreground' : 'text-gray-400 italic'
        )}>
          {value || '尚未識別'}
        </div>
      </div>
    </div>
  );
}

const meddicItems = [
  { key: 'metrics', label: 'Metrics (量化指標)', abbr: 'M', color: 'bg-blue-500' },
  { key: 'economicBuyer', label: 'Economic Buyer (經濟決策者)', abbr: 'E', color: 'bg-purple-500' },
  { key: 'decisionCriteria', label: 'Decision Criteria (決策標準)', abbr: 'D', color: 'bg-green-500' },
  { key: 'decisionProcess', label: 'Decision Process (決策流程)', abbr: 'D', color: 'bg-teal-500' },
  { key: 'identifyPain', label: 'Identify Pain (痛點)', abbr: 'I', color: 'bg-orange-500' },
  { key: 'champion', label: 'Champion (支持者)', abbr: 'C', color: 'bg-pink-500' },
] as const;

export function MEDDICCard({ data, className }: MEDDICCardProps) {
  return (
    <Card className={cn('w-full', className)}>
      <CardHeader className="pb-2">
        <h3 className="text-lg font-semibold">MEDDIC 分析</h3>
      </CardHeader>
      <CardContent>
        <div className="divide-y">
          {meddicItems.map((item) => (
            <MEDDICItem
              key={item.key}
              label={item.label}
              abbr={item.abbr}
              value={data[item.key]}
              color={item.color}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
