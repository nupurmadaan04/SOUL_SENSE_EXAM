'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { HistoryChart } from '@/lib/dynamic-imports';
import { ExamResult as ChartResult } from '@/components/results/history-chart';
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
} from '@/components/ui';
import { useResults } from '@/hooks/useResults';

type NormalizedResult = {
  id: string;
  completedAt: string;
  score: number;
  durationSeconds: number | null;
};

const PAGE_SIZE = 6;

const normalizeResults = (
  raw: { id: number; completed_at: string; overall_score: number; duration_seconds: number }[]
): NormalizedResult[] => {
  return raw
    .map((item) => ({
      id: String(item.id),
      completedAt: item.completed_at,
      score: item.overall_score ?? 0,
      durationSeconds: item.duration_seconds ?? null,
    }))
    .filter((item) => Boolean(item.completedAt));
};

const formatDate = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
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

const getScoreTone = (score: number) => {
  if (score >= 85) return 'bg-emerald-100 text-emerald-700 border-emerald-200';
  if (score >= 70) return 'bg-blue-100 text-blue-700 border-blue-200';
  if (score >= 55) return 'bg-amber-100 text-amber-700 border-amber-200';
  return 'bg-rose-100 text-rose-700 border-rose-200';
};

export default function ResultsPage() {
  const {
    history: apiResults,
    loading: isLoading,
    error,
    fetchHistory,
    totalCount,
  } = useResults({
    initialPage: 1,
    initialPageSize: 100,
  });

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);
  const [results, setResults] = useState<NormalizedResult[]>([]);
  const [sortKey, setSortKey] = useState<'date' | 'score'>('date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [isChartVisible, setIsChartVisible] = useState(true);

  useEffect(() => {
    if (!apiResults) return;
    const normalized = normalizeResults(
      apiResults.map((item) => ({
        id: item.id,
        completed_at: item.timestamp,
        overall_score: item.total_score ?? 0,
        duration_seconds: 0,
      }))
    );
    setResults(normalized);
  }, [apiResults]);

  useEffect(() => {
    setCurrentPage(1);
  }, [sortKey, sortDirection, dateFrom, dateTo]);

  const filteredResults = useMemo(() => {
    const fromDate = dateFrom ? new Date(`${dateFrom}T00:00:00Z`) : null;
    const toDate = dateTo ? new Date(`${dateTo}T23:59:59.999Z`) : null;

    return results.filter((item) => {
      const completedDate = new Date(item.completedAt);
      if (Number.isNaN(completedDate.getTime())) return false;
      if (fromDate && completedDate < fromDate) return false;
      if (toDate && completedDate > toDate) return false;
      return true;
    });
  }, [results, dateFrom, dateTo]);

  const sortedResults = useMemo(() => {
    return [...filteredResults].sort((a, b) => {
      if (sortKey === 'score') {
        const diff = a.score - b.score;
        return sortDirection === 'asc' ? diff : -diff;
      }

      const aTime = new Date(a.completedAt).getTime();
      const bTime = new Date(b.completedAt).getTime();
      const diff = aTime - bTime;
      return sortDirection === 'asc' ? diff : -diff;
    });
  }, [filteredResults, sortKey, sortDirection]);

  const totalPages = Math.max(1, Math.ceil(sortedResults.length / PAGE_SIZE));
  const pagedResults = sortedResults.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const chartResults: ChartResult[] = useMemo(() => {
    return filteredResults.map((item) => ({
      id: item.id,
      timestamp: item.completedAt,
      score: item.score,
    }));
  }, [filteredResults]);

  const emptyState = !isLoading && !error && results.length === 0;

  return (
    <div
      className="relative overflow-hidden"
      style={
        {
          '--result-1': '#eef2ff',
          '--result-2': '#f0fdf4',
          '--result-3': '#fffbeb',
        } as React.CSSProperties
      }
    >
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-16 right-10 h-64 w-64 rounded-full bg-[radial-gradient(circle,var(--result-1),transparent_60%)] blur-2xl" />
        <div className="absolute -bottom-20 left-8 h-72 w-72 rounded-full bg-[radial-gradient(circle,var(--result-2),transparent_65%)] blur-2xl" />
        <div className="absolute top-40 left-1/2 h-48 w-48 -translate-x-1/2 rounded-full bg-[radial-gradient(circle,var(--result-3),transparent_65%)] blur-2xl" />
      </div>

      <div className="relative mx-auto flex w-full max-w-6xl flex-col gap-8">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-blue-600/70">Insights</p>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Results</h1>
            </div>
            <Button
              variant="outline"
              className="border-slate-200 bg-white/80"
              onClick={() => setIsChartVisible((prev) => !prev)}
            >
              {isChartVisible ? 'Hide trends' : 'Show trends'}
            </Button>
          </div>
          <p className="text-muted-foreground max-w-2xl">
            Track your assessment outcomes, compare progress, and revisit any session for deeper
            insights.
          </p>
        </div>

        {isChartVisible && (
          <div className="transition-opacity">
            <HistoryChart results={chartResults} timeRange="all" showCategories={false} />
          </div>
        )}

        <Card className="border-slate-200 bg-white/80 backdrop-blur">
          <CardHeader className="gap-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <CardTitle className="text-2xl text-slate-900">Past results</CardTitle>
                <CardDescription>Sort, filter, and open any assessment.</CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>Sort by</span>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                    value={sortKey}
                    onChange={(event) => setSortKey(event.target.value as 'date' | 'score')}
                  >
                    <option value="date">Date</option>
                    <option value="score">Score</option>
                  </select>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>Order</span>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                    value={sortDirection}
                    onChange={(event) => setSortDirection(event.target.value as 'asc' | 'desc')}
                  >
                    {sortKey === 'score' ? (
                      <>
                        <option value="desc">High to low</option>
                        <option value="asc">Low to high</option>
                      </>
                    ) : (
                      <>
                        <option value="desc">Newest</option>
                        <option value="asc">Oldest</option>
                      </>
                    )}
                  </select>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>From</span>
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(event) => setDateFrom(event.target.value)}
                  className="w-[160px]"
                />
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>To</span>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(event) => setDateTo(event.target.value)}
                  className="w-[160px]"
                />
              </div>
              {(dateFrom || dateTo) && (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setDateFrom('');
                    setDateTo('');
                  }}
                >
                  Clear dates
                </Button>
              )}
            </div>
          </CardHeader>

          <CardContent>
            {isLoading ? (
              <div className="rounded-lg border border-dashed border-slate-200 bg-white/60 p-10 text-center">
                <p className="text-sm text-muted-foreground">Loading results...</p>
              </div>
            ) : error ? (
              <div className="rounded-lg border border-dashed border-rose-200 bg-rose-50/60 p-10 text-center">
                <p className="text-sm text-rose-700">{error}</p>
              </div>
            ) : emptyState ? (
              <div className="rounded-lg border border-dashed border-slate-200 bg-white/60 p-10 text-center">
                <p className="text-lg font-semibold text-slate-900">No results yet</p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Complete your first assessment to see trends and detailed results here.
                </p>
                <Button asChild className="mt-5">
                  <Link href="/exam">Start an assessment</Link>
                </Button>
              </div>
            ) : (
              <div className="space-y-6">
                {pagedResults.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-slate-200 bg-white/60 p-6 text-center text-sm text-muted-foreground">
                    No results match the selected date range.
                  </div>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2">
                    {pagedResults.map((result) => (
                      <Link key={result.id} href={`/results/${result.id}`} className="group">
                        <Card className="h-full border-slate-200 bg-white/90 transition-all hover:-translate-y-1 hover:shadow-lg">
                          <CardHeader className="space-y-3">
                            <div className="flex items-center justify-between gap-4">
                              <p className="text-sm font-semibold text-slate-900">
                                {formatDate(result.completedAt)}
                              </p>
                              <span
                                className={`rounded-full border px-3 py-1 text-xs font-semibold ${getScoreTone(
                                  result.score
                                )}`}
                              >
                                {result.score}%
                              </span>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              Duration: {formatDuration(result.durationSeconds)}
                            </p>
                          </CardHeader>
                          <CardContent>
                            <div className="flex items-center justify-between text-sm text-muted-foreground">
                              <span>Assessment ID: {result.id}</span>
                              <span className="font-medium text-blue-600 group-hover:translate-x-1 transition-transform">
                                View details →
                              </span>
                            </div>
                          </CardContent>
                        </Card>
                      </Link>
                    ))}
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-muted-foreground">
                    Showing {pagedResults.length} of {sortedResults.length} results
                    {totalCount > 0 ? ` (${totalCount} total)` : ''}
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                      disabled={currentPage === 1}
                    >
                      Previous
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      Page {currentPage} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                      disabled={currentPage === totalPages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
