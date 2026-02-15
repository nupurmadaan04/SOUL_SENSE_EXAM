import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Recommendation } from '@/types/results';
import { cn } from '@/lib/utils';

interface RecommendationCardProps {
  recommendation: Recommendation;
  className?: string;
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({ 
  recommendation,
  className 
}) => {
  const getPriorityStyles = (priority?: string) => {
    switch (priority) {
      case 'high':
        return {
          border: 'border-l-4 border-l-red-500',
          badge: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        };
      case 'medium':
        return {
          border: 'border-l-4 border-l-yellow-500',
          badge: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
        };
      case 'low':
        return {
          border: 'border-l-4 border-l-green-500',
          badge: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        };
      default:
        return {
          border: 'border-l-4 border-l-blue-500',
          badge: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
        };
    }
  };

  const styles = getPriorityStyles(recommendation.priority);

  return (
    <Card className={cn(styles.border, className)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <CardTitle className="text-lg">{recommendation.title}</CardTitle>
          <div className="flex gap-2">
            {recommendation.priority && (
              <span
                className={cn(
                  'px-2 py-1 text-xs font-medium rounded-full',
                  styles.badge
                )}
              >
                {recommendation.priority.toUpperCase()}
              </span>
            )}
            {recommendation.category && (
              <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200">
                {recommendation.category}
              </span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="text-sm leading-relaxed">
          {recommendation.description}
        </CardDescription>
      </CardContent>
    </Card>
  );
};

export default RecommendationCard;
