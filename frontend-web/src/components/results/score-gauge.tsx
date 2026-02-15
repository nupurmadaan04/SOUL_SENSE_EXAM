import React from 'react';
import { cn } from '@/lib/utils';

interface ScoreGaugeProps {
  score: number; // Score from 0-100
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  showPercentage?: boolean;
  animated?: boolean;
}

const ScoreGauge: React.FC<ScoreGaugeProps> = ({
  score,
  size = 'md',
  label = 'Overall Score',
  showPercentage = true,
  animated = true,
}) => {
  // Clamp score between 0 and 100
  const clampedScore = Math.min(Math.max(score, 0), 100);
  
  // Calculate color based on score
  const getColor = (score: number): string => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-blue-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getStrokeColor = (score: number): string => {
    if (score >= 80) return '#16a34a'; // green-600
    if (score >= 60) return '#2563eb'; // blue-600
    if (score >= 40) return '#ca8a04'; // yellow-600
    return '#dc2626'; // red-600
  };

  const sizes = {
    sm: { width: 120, height: 120, strokeWidth: 8, fontSize: 'text-2xl' },
    md: { width: 200, height: 200, strokeWidth: 12, fontSize: 'text-4xl' },
    lg: { width: 280, height: 280, strokeWidth: 16, fontSize: 'text-6xl' },
  };

  const { width, height, strokeWidth, fontSize } = sizes[size];
  const radius = (width - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clampedScore / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center space-y-4">
      <div className="relative" style={{ width, height }}>
        <svg
          width={width}
          height={height}
          className="transform -rotate-90"
        >
          {/* Background circle */}
          <circle
            cx={width / 2}
            cy={height / 2}
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={strokeWidth}
          />
          
          {/* Progress circle */}
          <circle
            cx={width / 2}
            cy={height / 2}
            r={radius}
            fill="none"
            stroke={getStrokeColor(clampedScore)}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={animated ? 'transition-all duration-1000 ease-out' : ''}
          />
        </svg>
        
        {/* Score text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn('font-bold', fontSize, getColor(clampedScore))}>
            {Math.round(clampedScore)}
            {showPercentage && <span className="text-2xl">%</span>}
          </span>
        </div>
      </div>
      
      {label && (
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
      )}
    </div>
  );
};

export default ScoreGauge;
