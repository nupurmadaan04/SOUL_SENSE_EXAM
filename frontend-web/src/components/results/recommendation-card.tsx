'use client';

import React, { useMemo, useState } from 'react';
import { Brain, HeartHandshake, Shield, Sparkles, Users } from 'lucide-react';
import { Recommendation } from '@/types/results';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

type RecommendationCardProps = {
  recommendation: Recommendation;
  isExpanded?: boolean;
  onToggle?: (id: number) => void;
};

const getIcon = (category?: string) => {
  const key = (category || '').toLowerCase();
  if (key.includes('self') || key.includes('awareness')) return Brain;
  if (key.includes('empathy') || key.includes('compassion')) return HeartHandshake;
  if (key.includes('social') || key.includes('relationships')) return Users;
  if (key.includes('resilience') || key.includes('regulation')) return Shield;
  return Sparkles;
};

const truncate = (text: string, limit: number) => {
  if (text.length <= limit) return text;
  return `${text.slice(0, limit).trim()}...`;
};

const getPriorityTone = (priority?: Recommendation['priority']) => {
  if (priority === 'high') return 'bg-rose-100 text-rose-700 border-rose-200';
  if (priority === 'medium') return 'bg-amber-100 text-amber-700 border-amber-200';
  if (priority === 'low') return 'bg-emerald-100 text-emerald-700 border-emerald-200';
  return 'bg-slate-100 text-slate-600 border-slate-200';
};

export default function RecommendationCard({
  recommendation,
  isExpanded,
  onToggle,
}: RecommendationCardProps) {
  const [internalExpanded, setInternalExpanded] = useState(false);
  const expanded = isExpanded ?? internalExpanded;
  const Icon = useMemo(() => getIcon(recommendation.category), [recommendation.category]);
  const description = expanded
    ? recommendation.description
    : truncate(recommendation.description, 140);

  const handleToggle = () => {
    if (onToggle) {
      onToggle(recommendation.id);
      return;
    }
    setInternalExpanded((prev) => !prev);
  };

  return (
    <Card className="border-slate-200 bg-white/90 shadow-sm">
      <CardContent className="space-y-3 pt-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-50 text-blue-600">
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">{recommendation.title}</p>
              {recommendation.category && (
                <span className="mt-1 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                  {recommendation.category}
                </span>
              )}
            </div>
          </div>
          <span
            className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${getPriorityTone(
              recommendation.priority
            )}`}
          >
            {recommendation.priority ? `${recommendation.priority} priority` : 'Suggested'}
          </span>
        </div>

        <p className="text-sm text-muted-foreground">{description}</p>

        {recommendation.description.length > 140 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleToggle}
            className="px-2"
            aria-label={
              expanded
                ? `Show less for ${recommendation.title}`
                : `Read more about ${recommendation.title}`
            }
          >
            {expanded ? 'Show less' : 'Read more'}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
