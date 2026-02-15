'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useExamStore } from '@/stores/examStore';

type ExamHistoryItem = {
  id: string | number;
  completed_at: string;
  overall_score: number;
};

const QUESTION_COUNT = 20;
const ESTIMATED_TIME = '15-20 minutes';
const HISTORY_KEY = 'exam-history';

export default function ExamPage() {
  const router = useRouter();
  const [history, setHistory] = useState<ExamHistoryItem[]>([]);

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

  useEffect(() => {
    if (typeof window === 'undefined') return;

    try {
      const stored = localStorage.getItem(HISTORY_KEY);
      if (!stored) return;

      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) {
        setHistory(parsed as ExamHistoryItem[]);
      } else if (parsed?.results && Array.isArray(parsed.results)) {
        setHistory(parsed.results as ExamHistoryItem[]);
      }
    } catch (error) {
      console.warn('Failed to parse exam history from storage.', error);
    }
  }, []);

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
              <h1 className="text-4xl font-semibold tracking-tight text-slate-900">EQ Assessment</h1>
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

          <Card variant="elevated" className="bg-[linear-gradient(135deg,var(--calm-1),var(--calm-2),var(--calm-3))]">
            <CardHeader>
              <CardTitle className="text-2xl text-slate-900">Assessment Details</CardTitle>
              <CardDescription>Know what to expect before you begin.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Estimated time</span>
                <span className="text-sm font-semibold text-slate-900">{ESTIMATED_TIME}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Number of questions</span>
                <span className="text-sm font-semibold text-slate-900">{QUESTION_COUNT}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Format</span>
                <span className="text-sm font-semibold text-slate-900">Likert scale responses</span>
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
            <Card variant="outlined" className="border-emerald-200 bg-white/80">
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
              {history.length === 0 ? (
                <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                  No past exams yet. Complete your first assessment to see your history.
                </div>
              ) : (
                <div className="space-y-4">
                  {history.slice(0, 3).map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-wrap items-center justify-between gap-2 border-b pb-3 last:border-b-0 last:pb-0"
                    >
                      <div>
                        <p className="text-sm font-semibold text-slate-900">
                          Completed {formatDate(item.completed_at)}
                        </p>
                        <p className="text-xs text-muted-foreground">Assessment ID: {item.id}</p>
                      </div>
                      <span className="text-sm font-semibold text-emerald-700">
                        Score {item.overall_score}%
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
