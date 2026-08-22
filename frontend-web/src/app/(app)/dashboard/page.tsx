'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import {
  DashboardSkeleton,
  BentoGrid,
} from '@/components/dashboard';
import type { ActivityItem } from '@/components/dashboard';

// Dynamic imports for dashboard components
const MoodWidget = dynamic(() => import('@/components/dashboard').then((mod) => mod.MoodWidget), {
  loading: () => <div className="h-full w-full animate-pulse bg-muted rounded-3xl" />,
  ssr: false,
});

const InsightCard = dynamic(() => import('@/components/dashboard').then((mod) => mod.InsightCard), {
  ssr: false,
});

import { DashboardCharts } from '@/lib/dynamic-imports';
import { apiClient } from '@/lib/api/client';
import { useAuth } from '@/hooks/useAuth';
import { profileApi, MentalHealthFullProfile } from '@/lib/api/profile';
import { PersonalizedAssessmentHub } from '@/components/dashboard/PersonalizedAssessmentHub';
import { MentalHealthProfileModal } from '@/components/profile/MentalHealthProfileModal';
import { MindfulnessGuideModal } from '@/components/dashboard/MindfulnessGuideModal';
import { Sparkles, UserCog, Flame, Trophy, ArrowRight, ShieldCheck, Activity, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

interface DashboardData {
  profile: any | null;
  exams: any[];
  journals: any[];
  mood: any | null;
  insights: Array<{ title: string; description: string; type: string; actionLabel: string; target?: string; actionType?: string }>;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isMindfulnessModalOpen, setIsMindfulnessModalOpen] = useState(false);
  const [mentalHealthProfile, setMentalHealthProfile] = useState<MentalHealthFullProfile | null>(null);

  useEffect(() => {
    profileApi
      .getMentalHealthProfile()
      .then((p) => setMentalHealthProfile(p))
      .catch((err) => console.warn('Could not load mental health profile on dashboard mount:', err));
  }, []);

  const {
    data: examsData,
    isLoading: examsLoading,
    refetch: refetchExams,
  } = useQuery({
    queryKey: ['dashboard', 'exams'],
    queryFn: async () => {
      try {
        const response = await apiClient<any>('/exams/history?page=1&page_size=5');
        return response.assessments || [];
      } catch (e) {
        return [];
      }
    },
    staleTime: 60 * 1000,
  });

  const {
    data: journalsData,
    isLoading: journalsLoading,
    refetch: refetchJournals,
  } = useQuery({
    queryKey: ['dashboard', 'journals'],
    queryFn: async () => {
      try {
        const response = await apiClient<any>('/journal/?limit=5');
        return response.entries || [];
      } catch (e) {
        return [];
      }
    },
    staleTime: 60 * 1000,
  });

  const data: DashboardData = {
    profile: user,
    exams: examsData || [],
    journals: journalsData || [],
    mood: null,
    insights: [
      {
        title: 'Sleep Pattern',
        description: 'You tend to score higher on EQ assessments when you get 7+ hours of sleep.',
        type: 'trend',
        actionLabel: 'Analyze Pattern',
        target: '/profile',
      },
      {
        title: 'Mindfulness Tip',
        description: 'Try a 5-minute breathing reflection before your next exam to reduce anxiety.',
        type: 'tip',
        actionLabel: 'View Guide',
        actionType: 'mindfulness_modal',
      },
      {
        title: 'Security & Privacy',
        description: 'Your psychological logs and health factors are end-to-end protected and private.',
        type: 'safety',
        actionLabel: 'Learn more',
        target: '/settings#privacy',
      },
    ],
  };

  const handleInsightAction = (insight: any) => {
    if (insight.actionType === 'mindfulness_modal') {
      setIsMindfulnessModalOpen(true);
    } else if (insight.target) {
      router.push(insight.target);
    }
  };

  const getDisplayName = () => {
    if (mentalHealthProfile?.first_name) return mentalHealthProfile.first_name;
    if (user?.first_name) return user.first_name;
    if (user?.name && user.name !== user.username) {
      return user.name.split(' ')[0];
    }
    if (user?.username) {
      const clean = user.username.replace(/[0-9_]/g, '');
      if (clean.length >= 2) {
        return clean.charAt(0).toUpperCase() + clean.slice(1);
      }
      return user.username;
    }
    return 'User';
  };

  const userName = getDisplayName();

  return (
    <div className="p-4 md:p-10 space-y-10 max-w-7xl mx-auto">
      {/* Top Banner & Profile Quick Action */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight bg-gradient-to-r from-primary to-primary/50 bg-clip-text text-transparent">
            Personal Emotional Dashboard
          </h1>
          <p className="text-muted-foreground text-sm sm:text-base font-medium">
            Welcome back, <span className="text-foreground font-bold">{userName}</span>. Here&apos;s your holistic mental and emotional wellbeing profile.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => setIsProfileModalOpen(true)}
            className="gap-2 rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90 shadow-md shadow-primary/20 text-xs font-bold uppercase tracking-wider"
          >
            <UserCog className="w-4 h-4" />
            <span>Health & Emotional Profile</span>
          </Button>
        </div>
      </div>

      {/* PERSONALIZED ASSESSMENT HUB */}
      <PersonalizedAssessmentHub
        userProfile={mentalHealthProfile}
        onOpenProfileEditor={() => setIsProfileModalOpen(true)}
        onProfileUpdated={(updated) => setMentalHealthProfile(updated)}
      />

      {/* OVERVIEW BENTO GRID */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-foreground">
            Wellbeing & Activity Overview
          </h2>
          <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            Live sync active
          </div>
        </div>

        <BentoGrid className="auto-rows-[20.5rem]">
          {/* Row 1 - Card 1: Dashboard Chart with Filters */}
          <div className="h-full">
            <DashboardCharts />
          </div>

          {/* Row 1 - Card 2: Daily Mood Check-in Widget */}
          <div className="h-full">
            <MoodWidget />
          </div>

          {/* Row 1 - Card 3: Growth Streak & Quick Assessment Action */}
          <div className="border border-border/80 bg-card/90 backdrop-blur-md rounded-3xl p-6 shadow-xl flex flex-col justify-between h-full group overflow-hidden">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-2xl bg-orange-500/10 text-orange-500">
                  <Flame className="h-5 w-5 fill-orange-500" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-foreground">Growth Streak</h3>
                  <p className="text-[11px] text-muted-foreground">Daily mindfulness continuity</p>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-full bg-orange-500/10 text-orange-500 text-xs font-black">
                3 Days 🔥
              </span>
            </div>

            <div className="p-4 rounded-2xl bg-muted/20 border border-border/40 space-y-2 my-2">
              <div className="flex items-center justify-between text-xs font-bold">
                <span className="text-foreground">Level: Empathy Explorer</span>
                <span className="text-primary">75% to Level 2</span>
              </div>
              <div className="w-full bg-muted/60 h-2 rounded-full overflow-hidden">
                <div className="bg-gradient-to-r from-primary to-secondary h-full rounded-full w-3/4" />
              </div>
              <p className="text-[10px] text-muted-foreground">
                Next reward: Advanced Emotional Resilience Benchmark
              </p>
            </div>

            <div className="pt-2">
              <Link href="/exam">
                <Button className="w-full rounded-xl gap-2 font-bold text-xs uppercase tracking-wider bg-primary text-primary-foreground hover:bg-primary/90 shadow-md">
                  <Activity className="h-4 w-4" />
                  Take Assessment
                  <ArrowRight className="h-3.5 w-3.5 ml-auto" />
                </Button>
              </Link>
            </div>
          </div>

          {/* Row 2 - Insight Cards with active onAction routing */}
          {data.insights.map((insight, idx) => (
            <div key={`insight-${idx}`} className="h-full">
              <InsightCard
                insight={{
                  title: insight.title,
                  content: insight.description,
                  type: insight.type as any,
                  actionLabel: insight.actionLabel,
                }}
                onDismiss={() => {}}
                onAction={() => handleInsightAction(insight)}
                className="md:col-span-1"
              />
            </div>
          ))}
        </BentoGrid>
      </div>

      {/* Mental & Emotional Health Profile Modal */}
      <MentalHealthProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        onSaved={(updated) => setMentalHealthProfile(updated)}
      />

      {/* Mindfulness & Breathing Guide Modal */}
      <MindfulnessGuideModal
        isOpen={isMindfulnessModalOpen}
        onClose={() => setIsMindfulnessModalOpen(false)}
      />
    </div>
  );
}
