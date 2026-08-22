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
} from '@/components/ui';
import { useResults } from '@/hooks/useResults';
import { Award, TrendingUp, Calendar, Clock, ArrowRight, Activity, Sparkles, CheckCircle2, BarChart2 } from 'lucide-react';
import { cn } from '@/lib/utils';

type NormalizedResult = {
  id: string;
  completedAt: string;
  score: number;
  sentiment: number;
  durationSeconds: number | null;
  reflection?: string;
};

const PAGE_SIZE = 6;

const formatDate = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || 'Recent';
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date);
};

const getScoreTone = (score: number) => {
  if (score >= 75) return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30';
  if (score >= 60) return 'bg-blue-500/10 text-blue-500 border-blue-500/30';
  if (score >= 45) return 'bg-amber-500/10 text-amber-500 border-amber-500/30';
  return 'bg-rose-500/10 text-rose-500 border-rose-500/30';
};

export default function ResultsPage() {
  const {
    history: apiResults,
    loading: isLoading,
    error,
    fetchHistory,
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
  const [currentPage, setCurrentPage] = useState(1);
  const [isChartVisible, setIsChartVisible] = useState(true);

  useEffect(() => {
    if (!apiResults || !Array.isArray(apiResults)) return;
    const normalized = apiResults
      .map((item: any) => ({
        id: String(item.id || item.session_id || Math.random()),
        completedAt: item.timestamp || item.completed_at || item.created_at || new Date().toISOString(),
        score: item.total_score ?? item.overall_score ?? item.score ?? 0,
        sentiment: item.sentiment_score ?? 0,
        durationSeconds: item.duration_seconds ?? null,
        reflection: item.reflection_text || item.reflection || '',
      }))
      .filter((item) => Boolean(item.completedAt));
    setResults(normalized);
  }, [apiResults]);

  const sortedResults = useMemo(() => {
    return [...results].sort((a, b) => {
      if (sortKey === 'score') {
        const diff = a.score - b.score;
        return sortDirection === 'asc' ? diff : -diff;
      }
      const aTime = new Date(a.completedAt).getTime();
      const bTime = new Date(b.completedAt).getTime();
      return sortDirection === 'asc' ? aTime - bTime : bTime - aTime;
    });
  }, [results, sortKey, sortDirection]);

  const totalPages = Math.max(1, Math.ceil(sortedResults.length / PAGE_SIZE));
  const pagedResults = sortedResults.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const chartResults: ChartResult[] = useMemo(() => {
    return sortedResults.map((item) => ({
      id: item.id,
      timestamp: item.completedAt,
      score: item.score,
    }));
  }, [sortedResults]);

  const latestScore = results.length > 0 ? results[0].score : 0;
  const avgScore = results.length > 0 ? Math.round(results.reduce((acc, r) => acc + r.score, 0) / results.length) : 0;
  const totalExams = results.length;

  return (
    <div className="p-4 md:p-10 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-border/40 pb-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-primary/10 text-primary border border-primary/20">
              Emotional Analytics
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground">
            Assessment Results & History
          </h1>
          <p className="text-muted-foreground text-sm max-w-2xl">
            Track your emotional intelligence progression, review past sessions, and identify longitudinal wellbeing trends.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            className="border-border/80 bg-card/80 text-foreground hover:bg-muted/80 rounded-2xl text-xs font-bold"
            onClick={() => setIsChartVisible((prev) => !prev)}
          >
            {isChartVisible ? 'Hide Trend Chart' : 'Show Trend Chart'}
          </Button>
          <Link href="/exam">
            <Button className="rounded-2xl gap-2 bg-primary text-primary-foreground font-bold text-xs shadow-md">
              <Activity className="h-4 w-4" />
              New Assessment
            </Button>
          </Link>
        </div>
      </div>

      {/* Metrics Summary Row */}
      {results.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="border border-border/80 bg-card/90 backdrop-blur-md shadow-xl rounded-3xl p-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Latest EQ Score</span>
              <div className="p-2 rounded-2xl bg-primary/10 text-primary">
                <Award className="h-5 w-5" />
              </div>
            </div>
            <div className="text-3xl font-black text-foreground mt-3">{latestScore}%</div>
            <p className="text-[11px] text-muted-foreground mt-1">Recorded on {formatDate(results[0]?.completedAt)}</p>
          </Card>

          <Card className="border border-border/80 bg-card/90 backdrop-blur-md shadow-xl rounded-3xl p-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Average Resilience</span>
              <div className="p-2 rounded-2xl bg-emerald-500/10 text-emerald-500">
                <TrendingUp className="h-5 w-5" />
              </div>
            </div>
            <div className="text-3xl font-black text-foreground mt-3">{avgScore}%</div>
            <p className="text-[11px] text-muted-foreground mt-1">Across all completed assessments</p>
          </Card>

          <Card className="border border-border/80 bg-card/90 backdrop-blur-md shadow-xl rounded-3xl p-6">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Assessments Taken</span>
              <div className="p-2 rounded-2xl bg-purple-500/10 text-purple-500">
                <CheckCircle2 className="h-5 w-5" />
              </div>
            </div>
            <div className="text-3xl font-black text-foreground mt-3">{totalExams}</div>
            <p className="text-[11px] text-muted-foreground mt-1">Verified psychometric sessions</p>
          </Card>
        </div>
      )}

      {/* Main Content Area */}
      {isLoading ? (
        <div className="p-12 border border-border/80 bg-card/90 rounded-3xl shadow-xl animate-pulse text-center space-y-4">
          <div className="h-8 bg-muted/40 rounded w-1/4 mx-auto" />
          <div className="h-44 bg-muted/30 rounded-2xl" />
        </div>
      ) : results.length === 0 ? (
        /* Empty State */
        <Card className="border border-border/80 bg-card/90 backdrop-blur-md shadow-xl rounded-3xl p-12 text-center">
          <div className="w-16 h-16 rounded-3xl bg-primary/10 text-primary flex items-center justify-center mx-auto mb-4 border border-primary/20">
            <BarChart2 className="w-8 h-8" />
          </div>
          <h3 className="text-2xl font-bold text-foreground">No Assessment History Yet</h3>
          <p className="text-muted-foreground text-sm max-w-md mx-auto mt-2">
            Complete your first personalized or standard emotional intelligence assessment to start seeing your score trends and psychological analytics.
          </p>
          <div className="mt-6">
            <Link href="/exam">
              <Button size="lg" className="rounded-2xl gap-2 font-bold px-8 shadow-lg shadow-primary/20">
                <Activity className="h-4 w-4" />
                Start Your First Assessment
              </Button>
            </Link>
          </div>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* History Chart */}
          {isChartVisible && (
            <Card className="border border-border/80 bg-card/90 backdrop-blur-md shadow-xl rounded-3xl p-6">
              <CardHeader className="px-0 pt-0 pb-4">
                <CardTitle className="text-lg font-bold text-foreground">Performance Over Time</CardTitle>
                <CardDescription>Track your emotional intelligence index trends across recent evaluations.</CardDescription>
              </CardHeader>
              <CardContent className="px-0 pb-0">
                <HistoryChart results={chartResults} />
              </CardContent>
            </Card>
          )}

          {/* Past Results Table */}
          <Card className="border border-border/80 bg-card/90 backdrop-blur-md shadow-xl rounded-3xl p-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-border/40">
              <h3 className="text-lg font-bold text-foreground">Past Assessments</h3>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-muted-foreground">Sort by:</span>
                <select
                  value={sortKey}
                  onChange={(e) => setSortKey(e.target.value as 'date' | 'score')}
                  className="px-3 py-1.5 rounded-xl border border-border/80 bg-background text-foreground text-xs font-semibold cursor-pointer"
                >
                  <option value="date">Date</option>
                  <option value="score">Score</option>
                </select>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'))}
                  className="text-xs font-semibold rounded-xl"
                >
                  {sortDirection === 'desc' ? 'Newest / Highest' : 'Oldest / Lowest'}
                </Button>
              </div>
            </div>

            <div className="divide-y divide-border/40 mt-2">
              {pagedResults.map((item) => (
                <div
                  key={item.id}
                  className="py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-colors hover:bg-muted/20 rounded-2xl px-3"
                >
                  <div className="flex items-center gap-3.5">
                    <div className="p-3 rounded-2xl bg-primary/10 text-primary shrink-0">
                      <Activity className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-foreground text-sm">
                          Completed on {formatDate(item.completedAt)}
                        </span>
                        <span className={cn('px-2.5 py-0.5 rounded-full text-[10px] font-bold border', getScoreTone(item.score))}>
                          Score {item.score}%
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Session ID: {item.id.slice(0, 16)}... • Status: Validated
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                    <Link href={`/results/${item.id}`}>
                      <Button variant="outline" size="sm" className="rounded-xl text-xs font-bold gap-1 border-border/80">
                        View Analysis
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 mt-4 border-t border-border/40">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  className="rounded-xl text-xs font-semibold"
                >
                  Previous
                </Button>
                <span className="text-xs font-semibold text-muted-foreground">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  className="rounded-xl text-xs font-semibold"
                >
                  Next
                </Button>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
