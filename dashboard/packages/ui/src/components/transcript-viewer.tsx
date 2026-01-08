import * as React from 'react';
import { cn } from '../lib/utils';

export interface TranscriptSegment {
  speaker?: string;
  text: string;
  start?: number;
  end?: number;
}

export interface TranscriptViewerProps {
  segments: TranscriptSegment[];
  currentTime?: number;
  onSegmentClick?: (segment: TranscriptSegment, index: number) => void;
  className?: string;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function getSpeakerColor(speaker: string): string {
  const colors = [
    'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  ];
  const hash = speaker.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

export function TranscriptViewer({
  segments,
  currentTime,
  onSegmentClick,
  className,
}: TranscriptViewerProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);

  const isSegmentActive = (segment: TranscriptSegment): boolean => {
    if (currentTime === undefined || segment.start === undefined || segment.end === undefined) {
      return false;
    }
    return currentTime >= segment.start && currentTime < segment.end;
  };

  return (
    <div
      ref={containerRef}
      className={cn('space-y-3 overflow-y-auto', className)}
    >
      {segments.map((segment, index) => {
        const active = isSegmentActive(segment);
        return (
          <div
            key={index}
            className={cn(
              'flex gap-3 p-3 rounded-lg transition-colors',
              active && 'bg-accent',
              onSegmentClick && 'cursor-pointer hover:bg-accent/50'
            )}
            onClick={() => onSegmentClick?.(segment, index)}
          >
            {segment.start !== undefined && (
              <span className="text-xs text-muted-foreground whitespace-nowrap mt-1">
                {formatTime(segment.start)}
              </span>
            )}
            <div className="flex-1">
              {segment.speaker && (
                <span
                  className={cn(
                    'inline-block px-2 py-0.5 rounded text-xs font-medium mb-1',
                    getSpeakerColor(segment.speaker)
                  )}
                >
                  {segment.speaker}
                </span>
              )}
              <p className={cn('text-sm leading-relaxed', active && 'font-medium')}>
                {segment.text}
              </p>
            </div>
          </div>
        );
      })}
      {segments.length === 0 && (
        <div className="text-center text-muted-foreground py-8">
          尚無逐字稿內容
        </div>
      )}
    </div>
  );
}
