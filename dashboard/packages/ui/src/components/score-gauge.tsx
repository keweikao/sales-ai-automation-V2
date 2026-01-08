import * as React from 'react';
import { cn } from '../lib/utils';

export interface ScoreGaugeProps {
  score: number;
  maxScore?: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  label?: string;
  className?: string;
}

function getScoreColor(score: number, max: number): string {
  const percentage = (score / max) * 100;
  if (percentage >= 70) return 'text-green-600 dark:text-green-400';
  if (percentage >= 40) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

function getScoreRingColor(score: number, max: number): string {
  const percentage = (score / max) * 100;
  if (percentage >= 70) return 'stroke-green-500';
  if (percentage >= 40) return 'stroke-yellow-500';
  return 'stroke-red-500';
}

const sizeConfig = {
  sm: { width: 64, strokeWidth: 4, fontSize: 'text-sm' },
  md: { width: 96, strokeWidth: 6, fontSize: 'text-xl' },
  lg: { width: 128, strokeWidth: 8, fontSize: 'text-3xl' },
};

export function ScoreGauge({
  score,
  maxScore = 100,
  size = 'md',
  showLabel = true,
  label = 'MEDDIC',
  className,
}: ScoreGaugeProps) {
  const config = sizeConfig[size];
  const radius = (config.width - config.strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const percentage = Math.min(score / maxScore, 1);
  const strokeDashoffset = circumference * (1 - percentage);

  return (
    <div className={cn('flex flex-col items-center', className)}>
      <div className="relative" style={{ width: config.width, height: config.width }}>
        <svg
          width={config.width}
          height={config.width}
          viewBox={`0 0 ${config.width} ${config.width}`}
          className="transform -rotate-90"
        >
          {/* Background circle */}
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={config.strokeWidth}
            className="text-gray-200 dark:text-gray-700"
          />
          {/* Progress circle */}
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            strokeWidth={config.strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={cn('transition-all duration-500', getScoreRingColor(score, maxScore))}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn('font-bold', config.fontSize, getScoreColor(score, maxScore))}>
            {Math.round(score)}
          </span>
        </div>
      </div>
      {showLabel && (
        <span className="mt-2 text-sm text-muted-foreground">{label}</span>
      )}
    </div>
  );
}
