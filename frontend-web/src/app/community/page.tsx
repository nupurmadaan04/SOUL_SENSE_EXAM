'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import dynamic from 'next/dynamic';
import {
  StatsCard,
  ActivityAreaChart,
  ContributionMixChart,
  DashboardSkeleton,
  Leaderboard,
  ReviewerMetrics,
  ActivityPulse,
  GoodFirstIssues,
  ProjectRoadmap,
} from '@/components/dashboard';
import { MOCK_DASHBOARD_DATA } from '@/lib/dashboard-mock-data';
import { MissionControl } from '@/components/mission-control';
import { Users, Star, GitMerge, GitCommit, ArrowRight, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Dynamically import heavy/browser-only visualizations to prevent SSR errors
const ForceDirectedGraph = dynamic(
  () =>
    import('@/components/dashboard/charts/force-directed-graph').then(
      (mod) => mod.ForceDirectedGraph
    ),
  { ssr: false, loading: () => <div className="h-64 rounded-2xl bg-slate-100 dark:bg-slate-800/50 animate-pulse" /> }
);

const RepositorySunburst = dynamic(
  () =>
    import('@/components/dashboard/charts/repository-sunburst').then(
      (mod) => mod.RepositorySunburst
    ),
  { ssr: false, loading: () => <div className="h-64 rounded-2xl bg-slate-100 dark:bg-slate-800/50 animate-pulse" /> }
);

export default function CommunityDashboard() {
  const [mounted, setMounted] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'mission-control'>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any>(MOCK_DASHBOARD_DATA);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    let isSubscribed = true;

    async function fetchData() {
      try {
        const host = typeof window !== 'undefined' ? (window.location.hostname || 'localhost') : '127.0.0.1';
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || `http://${host}:8000/api/v1`;
        
        const fetchWithTimeout = async (url: string, timeoutMs: number = 4000) => {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
          try {
            const res = await fetch(url, { signal: controller.signal });
            clearTimeout(timeoutId);
            return res;
          } catch (e) {
            clearTimeout(timeoutId);
            return null;
          }
        };

        const [
          statsRes,
          contributorsRes,
          activityRes,
          mixRes,
          reviewsRes,
          graphRes,
          sunburstRes,
          pulseRes,
          issuesRes,
          roadmapRes,
        ] = await Promise.all([
          fetchWithTimeout(`${API_BASE}/community/stats`),
          fetchWithTimeout(`${API_BASE}/community/contributors?limit=100`),
          fetchWithTimeout(`${API_BASE}/community/activity`),
          fetchWithTimeout(`${API_BASE}/community/mix`),
          fetchWithTimeout(`${API_BASE}/community/reviews`),
          fetchWithTimeout(`${API_BASE}/community/graph`),
          fetchWithTimeout(`${API_BASE}/community/sunburst`),
          fetchWithTimeout(`${API_BASE}/community/pulse`),
          fetchWithTimeout(`${API_BASE}/community/issues`),
          fetchWithTimeout(`${API_BASE}/community/roadmap`),
        ]);

        if (statsRes && statsRes.ok) {
          const stats = await statsRes.json();
          const contributors = (contributorsRes && contributorsRes.ok) ? await contributorsRes.json() : MOCK_DASHBOARD_DATA.contributors;
          const activity = (activityRes && activityRes.ok) ? await activityRes.json() : MOCK_DASHBOARD_DATA.activity;
          const mix = (mixRes && mixRes.ok) ? await mixRes.json() : MOCK_DASHBOARD_DATA.mix;
          const reviews = (reviewsRes && reviewsRes.ok) ? await reviewsRes.json() : MOCK_DASHBOARD_DATA.reviews;
          const graph = (graphRes && graphRes.ok) ? await graphRes.json() : MOCK_DASHBOARD_DATA.graph;
          const sunburst = (sunburstRes && sunburstRes.ok) ? await sunburstRes.json() : MOCK_DASHBOARD_DATA.sunburst;
          const pulse = (pulseRes && pulseRes.ok) ? await pulseRes.json() : MOCK_DASHBOARD_DATA.pulse;
          const issues = (issuesRes && issuesRes.ok) ? await issuesRes.json() : MOCK_DASHBOARD_DATA.issues;
          const roadmap = (roadmapRes && roadmapRes.ok) ? await roadmapRes.json() : MOCK_DASHBOARD_DATA.roadmap;

          if (isSubscribed) {
            setData({
              stats,
              contributors,
              activity,
              mix,
              reviews,
              graph,
              sunburst,
              pulse,
              issues,
              roadmap,
            });
          }
        } else {
          if (isSubscribed) {
            setData(MOCK_DASHBOARD_DATA);
          }
        }
      } catch (err) {
        console.warn('Failed to fetch community data, using fallback mock cache:', err);
        if (isSubscribed) {
          setData(MOCK_DASHBOARD_DATA);
        }
      } finally {
        if (isSubscribed) {
          setLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      isSubscribed = false;
    };
  }, []);

  if (!mounted || loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 font-sans transition-colors duration-500">
        <div className="max-w-7xl mx-auto px-6 md:px-8 space-y-8">
          <div className="h-14 md:h-20" aria-hidden="true" />
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50 pl-1">
            Soul Sense Community Hub
          </h1>
          <DashboardSkeleton />
        </div>
      </div>
    );
  }

  const safeData = data || MOCK_DASHBOARD_DATA;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 font-sans transition-colors duration-500">
      <div className="max-w-7xl mx-auto px-6 md:px-8 space-y-8">
        <div className="h-14 md:h-20" aria-hidden="true" />
        {/* Header Section: Tabs & Unified Controls */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row justify-between items-center gap-6"
        >
          {/* Tab Switcher */}
          <div className="flex p-1 bg-slate-200/50 dark:bg-slate-800/50 rounded-full border border-slate-200/50 dark:border-white/5 backdrop-blur-sm relative">
            {['overview', 'mission-control'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab as any)}
                className={cn(
                  'relative z-10 px-6 py-2 text-sm font-bold transition-colors duration-300',
                  activeTab === tab
                    ? 'text-slate-900 dark:text-white'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
                )}
              >
                {tab === 'overview' ? 'Overview' : 'Mission Control'}
                {activeTab === tab && (
                  <motion.div
                    layoutId="community-page-active-tab"
                    className="absolute inset-0 bg-white dark:bg-slate-900 rounded-full shadow-sm z-[-1]"
                    transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                  />
                )}
              </button>
            ))}
          </div>

          {/* System Log & Action Button */}
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <ActivityPulse events={safeData?.pulse || MOCK_DASHBOARD_DATA.pulse} />
            <motion.a
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              href="https://github.com/nupurmadaan04/SOUL_SENSE_EXAM/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22"
              target="_blank"
              className="group relative px-5 py-2.5 bg-slate-900 dark:bg-white text-white dark:text-slate-950 font-bold text-xs rounded-full shadow-lg hover:shadow-xl transition-all flex items-center gap-2 overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 via-blue-500/10 to-blue-500/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000 ease-in-out" />
              <span className="relative z-10">Contribute</span>
              <ArrowRight className="w-3.5 h-3.5 relative z-10 group-hover:translate-x-0.5 transition-transform" />
            </motion.a>
          </div>
        </motion.div>

        {/* Tab Content */}
        <div className="min-h-[600px] relative">
          <AnimatePresence mode="wait">
            {activeTab === 'overview' ? (
              <motion.div
                key="overview"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-12"
              >
                {/* Good First Issues Carousel */}
                <GoodFirstIssues data={safeData?.issues || MOCK_DASHBOARD_DATA.issues} />

                {/* Dynamic Bento Grid Layout */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {/* Primary Stats Section */}
                  <StatsCard
                    title="Contributors"
                    value={safeData.stats?.contributors || (safeData.contributors ? safeData.contributors.length : 43)}
                    icon={Users}
                    description="43+ active open-source contributors"
                    trend="up"
                    color="blue"
                  />
                  <StatsCard
                    title="Repository Stars"
                    value={safeData.stats?.repository?.stars || 15}
                    icon={Star}
                    description="Global project recognition"
                    trend="up"
                    color="purple"
                  />
                  <StatsCard
                    title="PR Throughput"
                    value={safeData.stats?.pull_requests?.total || 674}
                    icon={GitMerge}
                    description={`${safeData.stats?.pull_requests?.open || 0} open, ${safeData.stats?.pull_requests?.closed || 674} merged PRs`}
                    trend="up"
                    color="cyan"
                  />
                  <StatsCard
                    title="Commit Count"
                    value={safeData.stats?.commits?.total || 2014}
                    icon={GitCommit}
                    description="2,014 lifetime repository commits"
                    trend="up"
                    color="blue"
                  />

                  {/* Main Visualizations Row */}
                  <div className="col-span-full lg:col-span-2 transition-all duration-300">
                    <ActivityAreaChart data={safeData?.activity || MOCK_DASHBOARD_DATA.activity} />
                  </div>

                  <div className="col-span-full lg:col-span-2">
                    <ContributionMixChart data={safeData?.mix || MOCK_DASHBOARD_DATA.mix} />
                  </div>

                  <div className="col-span-full">
                    <Leaderboard contributors={safeData?.contributors || MOCK_DASHBOARD_DATA.contributors} />
                  </div>

                  <ForceDirectedGraph data={safeData?.graph || MOCK_DASHBOARD_DATA.graph} />

                  <RepositorySunburst data={safeData?.sunburst || MOCK_DASHBOARD_DATA.sunburst} />
                  <div className="col-span-full lg:col-span-2">
                    <ReviewerMetrics data={safeData?.reviews || MOCK_DASHBOARD_DATA.reviews} />
                  </div>

                  <div className="col-span-full">
                    <ProjectRoadmap data={safeData?.roadmap || MOCK_DASHBOARD_DATA.roadmap} />
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="mission-control"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="h-[calc(100vh-200px)]"
              >
                <MissionControl className="h-full" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
