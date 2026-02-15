'use client';

import React from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import CategoryBreakdown from '@/components/results/category-breakdown';
import RecommendationCard from '@/components/results/recommendation-card';
import { useResults } from '@/hooks/useResults';

const formatDate = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(date);
};

const formatDuration = (seconds: number | null) => {
  if (seconds === null || Number.isNaN(seconds)) return 'Not recorded';
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  if (minutes === 0) return `${remainingSeconds}s`;
  return `${minutes}m ${remainingSeconds}s`;
};

export default function ResultDetailPage() {
  const params = useParams();
  const resultId = String(params.id ?? '');
  const { result, isLoading, error } = useResults({
    resultId,
    enabledHistory: false,
  });

  if (isLoading) {
    return (
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>Loading result...</CardTitle>
          <CardDescription>Fetching your assessment details.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="max-w-xl border-rose-200 bg-rose-50/70">
        <CardHeader>
          <CardTitle>Unable to load result</CardTitle>
          <CardDescription>{error}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href="/results">Back to results</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return (
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>Result not found</CardTitle>
          <CardDescription>
            We could not locate that assessment. It may have been removed or cleared.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href="/results">Back to results</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.3em] text-blue-600/70">Assessment</p>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Result details</h1>
      </div>

      <Card className="max-w-2xl border-slate-200 bg-white/90">
        <CardHeader>
          <CardTitle>{formatDate(result.completed_at)}</CardTitle>
          <CardDescription>Assessment ID: {result.id}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <div>
            <p className="text-sm text-muted-foreground">Score</p>
            <p className="text-2xl font-semibold text-slate-900">{result.overall_score}%</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Duration</p>
            <p className="text-2xl font-semibold text-slate-900">
              {formatDuration(result.duration_seconds || null)}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Status</p>
            <p className="text-2xl font-semibold text-slate-900">Completed</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <Card className="border-slate-200 bg-white/90">
          <CardHeader>
            <CardTitle>Category breakdown</CardTitle>
            <CardDescription>See how you performed across EQ dimensions.</CardDescription>
          </CardHeader>
          <CardContent>
            {result.categories && result.categories.length > 0 ? (
              <CategoryBreakdown
                categories={result.categories.map((category) => {
                  const percentageScore =
                    typeof category.max_score === 'number' && category.max_score > 0
                      ? (category.score / category.max_score) * 100
                      : category.score;

                  return {
                    name: category.name,
                    score: percentageScore,
                  };
                })}
              />
            ) : (
              <div className="rounded-lg border border-dashed border-slate-200 bg-white/60 p-6 text-center text-sm text-muted-foreground">
                Category insights are not available for this assessment.
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white/90">
          <CardHeader>
            <CardTitle>Recommendations</CardTitle>
            <CardDescription>Personalized actions based on your results.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {result.recommendations && result.recommendations.length > 0 ? (
              result.recommendations.map((rec) => (
                <RecommendationCard key={rec.id} recommendation={rec} />
              ))
            ) : (
              <div className="rounded-lg border border-dashed border-slate-200 bg-white/60 p-6 text-center text-sm text-muted-foreground">
                Recommendations will appear here after your next assessment.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {result.reflection && (
        <Card className="max-w-2xl border-slate-200 bg-white/90">
          <CardHeader>
            <CardTitle>Reflection</CardTitle>
            <CardDescription>Your notes from this assessment.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{result.reflection}</p>
          </CardContent>
        </Card>
      )}

      <Button variant="outline" asChild>
        <Link href="/results">Back to results</Link>
      </Button>
    </div>
  );
}
