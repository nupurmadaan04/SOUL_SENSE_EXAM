'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import {
  DashboardSkeleton,
  BentoGrid,
  SectionWrapper,
} from '@/components/dashboard';
import type { ActivityItem } from '@/components/dashboard';

// Dynamic imports for heavy dashboard components
const WelcomeCard = dynamic(() => import('@/components/dashboard').then(mod => mod.WelcomeCard), {
  loading: () => <div className="h-full w-full animate-pulse bg-muted rounded-xl" />,
  ssr: false
});

const QuickActions = dynamic(() => import('@/components/dashboard').then(mod => mod.QuickActions), {
  ssr: false
});

const MoodWidget = dynamic(() => import('@/components/dashboard').then(mod => mod.MoodWidget), {
  loading: () => <div className="h-full w-full animate-pulse bg-muted rounded-xl" />,
  ssr: false
});

const RecentActivity = dynamic(() => import('@/components/dashboard').then(mod => mod.RecentActivity), {
  loading: () => <div className="h-full w-full animate-pulse bg-muted rounded-xl" />,
  ssr: false
});

const InsightCard = dynamic(() => import('@/components/dashboard').then(mod => mod.InsightCard), {
  ssr: false
});
// Dynamically import heavy chart components to reduce initial bundle size
import { DashboardCharts } from '@/lib/dynamic-imports';
import { apiClient } from '@/lib/api/client';
import { useAuth } from '@/hooks/useAuth';

interface DashboardData {
  profile: any | null;
  exams: any[];
  journals: any[];
  mood: any | null;
  insights: Array<{ title: string; description: string; type: string }>;
}

export default function DashboardPage() {
  const { user } = useAuth();

  const { data: examsData, isLoading: examsLoading, error: examsError, refetch: refetchExams } = useQuery({
    queryKey: ['dashboard', 'exams'],
    queryFn: async () => {
      const response = await apiClient<any>('/exams/history?page=1&page_size=5');
      return response.assessments || [];
    },
  });

  const { data: journalsData, isLoading: journalsLoading, error: journalsError, refetch: refetchJournals } = useQuery({
    queryKey: ['dashboard', 'journals'],
    queryFn: async () => {
      const response = await apiClient<any>('/journal/?limit=5');
      return response.entries || [];
    },
  });

  const data: DashboardData = {
    profile: user,
    exams: examsData || [],
    journals: journalsData || [],
    mood: null,
    insights: [
      {
        title: 'Sleep Pattern',
        description:
          'You tend to score higher on EQ assessments when you get 7+ hours of sleep.',
        type: 'trend',
      },
      {
        title: 'Mindfulness Tip',
        description:
          'Try a 5-minute breathing exercise before your next exam to reduce anxiety.',
        type: 'tip',
      },
    ],
  };

  const loading = examsLoading || journalsLoading;
  const error = examsError || journalsError;

  // Combine exams and journals into activities
  const activities: ActivityItem[] = [
    ...data.exams.map((e) => ({
      id: e.id,
      type: 'assessment' as const,
      title: `EQ Assessment - Score: ${e.total_score || e.score || 0}%`,
      timestamp: e.timestamp || e.created_at,
      href: `/results/${e.id}`,
    })),
    ...data.journals.map((j) => ({
      id: j.id,
      type: 'journal' as const,
      title:
        j.content?.substring(0, 30) + (j.content?.length > 30 ? '...' : '') || 'Untitled Journal',
      timestamp: j.created_at || j.timestamp,
      href: `/journal/${j.id}`,
    })),
  ];

  if (loading && !data.profile) {
    return (
      <div className="p-4 md:p-8 space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-2">Loading your overview...</p>
        </div>
        <DashboardSkeleton />
      </div>
    );
  }

  // Calculate the most recent activity date dynamically
  const dates = activities
    .map((a) => new Date(a.timestamp).getTime())
    .filter((time) => !isNaN(time));
  const recentActivityDate = dates.length > 0 ? new Date(Math.max(...dates)) : undefined;

  const userName = user?.name?.split(' ')[0];

  return (
    <div className="p-4 md:p-10 space-y-10 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="space-y-1">
          <h1 className="text-4xl font-black tracking-tight bg-gradient-to-r from-primary to-primary/50 bg-clip-text text-transparent">
            Dashboard
          </h1>
          <p className="text-muted-foreground text-lg font-medium opacity-80">
            Welcome back, {userName || 'User'}. Here&apos;s your mental wellbeing at a glance.
          </p>
        </div>
      </div>

      <BentoGrid className="auto-rows-[20rem]">
        {/* Row 1 */}
        <SectionWrapper isLoading={false} error={error} onRetry={() => { refetchExams(); refetchJournals(); }}>
          <WelcomeCard userName={userName} lastActivity={recentActivityDate} />
        </SectionWrapper>

        <SectionWrapper isLoading={false} error={error} onRetry={() => { refetchExams(); refetchJournals(); }}>
          <QuickActions />
        </SectionWrapper>

        {/* Charts Section */}
        <SectionWrapper isLoading={false} error={error} onRetry={() => { refetchExams(); refetchJournals(); }}>
          <DashboardCharts />
        </SectionWrapper>

        {/* Row 2 */}
        <SectionWrapper isLoading={false} error={error} onRetry={() => { refetchExams(); refetchJournals(); }}>
          <MoodWidget />
        </SectionWrapper>

        <SectionWrapper isLoading={loading} error={error} onRetry={() => { refetchExams(); refetchJournals(); }}>
          <RecentActivity activities={activities} />
        </SectionWrapper>

        {/* AI Insights - Multiple */}
        {data.insights.map((insight, idx) => (
          <SectionWrapper
            key={`insight-${idx}`}
            isLoading={false}
            error={error}
            onRetry={() => { refetchExams(); refetchJournals(); }}
          >
            <InsightCard
              insight={{
                title: insight.title,
                content: insight.description,
                type: insight.type as any,
                actionLabel: insight.type === 'tip' ? 'View Guide' : 'Analyze Pattern',
              }}
              onDismiss={() => {
                // TODO: Implement dismiss functionality
                console.log('Dismiss insight:', idx);
              }}
              onAction={(ins) => console.log('Action for:', ins.title)}
              className="md:col-span-1"
            />
          </SectionWrapper>
        ))}

        {/* Additional Insight or Filler */}
        <SectionWrapper isLoading={false} error={error} onRetry={() => { refetchExams(); refetchJournals(); }}>
          <InsightCard
            insight={{
              title: 'Security & Privacy',
              content:
                'Your data is encrypted and only accessible by you. We prioritize your privacy.',
              type: 'safety',
            }}
            onDismiss={() => { }}
            onAction={() => { }}
            className="md:col-span-1"
          />
        </SectionWrapper>
      </BentoGrid>
    </div>
  );
}
