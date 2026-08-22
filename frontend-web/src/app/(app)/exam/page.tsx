'use client';

import React, { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui';
import { useExamStore } from '@/stores/examStore';
import { useApi, useOnlineStatus } from '@/hooks/useApi';
import { resultsApi } from '@/lib/api/results';
import { Skeleton, OfflineBanner } from '@/components/common';

const QUESTION_COUNT = 20;
const ESTIMATED_TIME = '15-20 minutes';

export default function ExamPage() {
  const router = useRouter();
  const isOnline = useOnlineStatus();

  const { data: historyData, loading: historyLoading } = useApi({
    apiFn: () => resultsApi.getHistory(1, 5),
    deps: [],
  });

  const {
    questions,
    startTime,
    isCompleted,
    resetExam,
    getAnsweredCount,
    getProgressPercentage,
    _hasHydrated,
  } = useExamStore();

  const answeredCount = getAnsweredCount();
  const progressPercentage = getProgressPercentage();

  const hasResume = useMemo(() => {
    if (!_hasHydrated) return false;
    return questions.length > 0 && !isCompleted && Boolean(startTime);
  }, [_hasHydrated, questions.length, isCompleted, startTime]);

  const handleStartAssessment = () => {
    resetExam();
    router.push('/exam/start');
  };

  const handleResumeAssessment = () => {
    router.push('/exam/resume');
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

  return (
    <div
      className="relative overflow-hidden"
      style={
        {
          '--calm-1': '#ecfeff',
          '--calm-2': '#eff6ff',
          '--calm-3': '#f0fdf4',
        } as React.CSSProperties
      }
    >
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-20 right-0 h-64 w-64 rounded-full bg-[radial-gradient(circle,rgba(14,116,144,0.15),transparent_60%)] blur-2xl" />
        <div className="absolute -bottom-24 left-0 h-72 w-72 rounded-full bg-[radial-gradient(circle,rgba(34,197,94,0.14),transparent_60%)] blur-2xl" />
      </div>

      <div className="container mx-auto px-4 py-10 max-w-6xl relative">
        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-6">
            <div className="space-y-3">
              <p className="text-sm uppercase tracking-[0.2em] text-emerald-700/80">Assessment</p>
              <h1 className="text-4xl font-semibold tracking-tight text-foreground">
                EQ Assessment
              </h1>
              <p className="text-muted-foreground text-base leading-relaxed">
                Measure how you perceive, process, and respond to emotions in daily life. This
                assessment explores self-awareness, empathy, and emotional regulation to help you
                understand your current strengths and growth areas.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <Button
                size="lg"
                onClick={handleStartAssessment}
                className="h-12 px-8 text-base shadow-lg shadow-emerald-500/20"
              >
                Start Assessment
              </Button>
              <p className="text-sm text-muted-foreground">
                {hasResume
                  ? 'Starting fresh will reset your current progress.'
                  : 'You can pause anytime and resume later.'}
              </p>
            </div>
          </div>

          <Card
            className="border-border/80 bg-card/90 backdrop-blur-md shadow-xl"
          >
            <CardHeader>
              <CardTitle className="text-2xl text-foreground">Assessment Details</CardTitle>
              <CardDescription>Know what to expect before you begin.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Estimated time</span>
                <span className="text-sm font-semibold text-foreground">{ESTIMATED_TIME}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Number of questions</span>
                <span className="text-sm font-semibold text-foreground">{QUESTION_COUNT}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Format</span>
                <span className="text-sm font-semibold text-foreground">
                  Likert scale responses
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-3">
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="text-xl">What this measures</CardTitle>
              <CardDescription>Key EQ domains covered in the assessment.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>Self-awareness and emotional clarity</p>
              <p>Empathy and social insight</p>
              <p>Regulation and resilience under pressure</p>
            </CardContent>
          </Card>

          <Card className="h-full">
            <CardHeader>
              <CardTitle className="text-xl">Instructions</CardTitle>
              <CardDescription>Stay relaxed and answer honestly.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>Read each question carefully before responding.</p>
              <p>There are no right or wrong answers.</p>
              <p>Choose the response that feels most accurate today.</p>
            </CardContent>
          </Card>

          <Card className="h-full">
            <CardHeader>
              <CardTitle className="text-xl">Your pace</CardTitle>
              <CardDescription>Progress is saved as you go.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>Pause and return anytime without losing answers.</p>
              <p>Complete the assessment when you feel ready.</p>
              <p>Results appear immediately after submission.</p>
            </CardContent>
          </Card>
        </div>

        {hasResume && (
          <div className="mt-10">
            <Card className="border-primary/40 bg-card/90 backdrop-blur-md shadow-lg">
              <CardHeader>
                <CardTitle className="text-xl">Resume your assessment</CardTitle>
                <CardDescription>
                  You have an incomplete exam in progress. Pick up where you left off.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center justify-between gap-4">
                <div className="space-y-1 text-sm text-muted-foreground">
                  <p>
                    Answered {answeredCount} of {questions.length} questions
                  </p>
                  <p>Progress: {progressPercentage}%</p>
                </div>
                <Button onClick={handleResumeAssessment} className="h-11 px-6">
                  Resume Assessment
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        <div className="mt-10">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Past assessments</CardTitle>
              <CardDescription>Your recent results appear here.</CardDescription>
            </CardHeader>
            <CardContent>
              {!isOnline && <OfflineBanner className="mb-4" />}
              {historyLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between border-b pb-3 last:border-b-0 last:pb-0"
                    >
                      <div className="space-y-1">
                        <Skeleton className="h-4 w-40" />
                        <Skeleton className="h-3 w-24" />
                      </div>
                      <Skeleton className="h-4 w-20" />
                    </div>
                  ))}
                </div>
              ) : !historyData?.assessments?.length ? (
                <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                  No past exams yet. Complete your first assessment to see your history.
                </div>
              ) : (
                <div className="space-y-4">
                  {historyData.assessments.slice(0, 5).map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-wrap items-center justify-between gap-2 border-b pb-3 last:border-b-0 last:pb-0"
                    >
                      <div>
                        <p className="text-sm font-semibold text-foreground">
                          Completed {formatDate(item.timestamp)}
                        </p>
                        <p className="text-xs text-muted-foreground">Assessment ID: {item.id}</p>
                      </div>
                      <span className="text-sm font-semibold text-emerald-700">
                        Score {item.total_score}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
