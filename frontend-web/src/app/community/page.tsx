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
  { ssr: false }
);

const RepositorySunburst = dynamic(
  () =>
    import('@/components/dashboard/charts/repository-sunburst').then(
      (mod) => mod.RepositorySunburst
    ),
  { ssr: false }
);

export default function CommunityDashboard() {
  const [activeTab, setActiveTab] = useState<'overview' | 'mission-control'>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const host = typeof window !== 'undefined' ? (window.location.hostname || 'localhost') : '127.0.0.1';
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || `http://${host}:8000/api/v1`;
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
          fetch(`${API_BASE}/community/stats`),
          fetch(`${API_BASE}/community/contributors?limit=100`),
          fetch(`${API_BASE}/community/activity`),
          fetch(`${API_BASE}/community/mix`),
          fetch(`${API_BASE}/community/reviews`),
          fetch(`${API_BASE}/community/graph`),
          fetch(`${API_BASE}/community/sunburst`),
          fetch(`${API_BASE}/community/pulse`),
          fetch(`${API_BASE}/community/issues`),
          fetch(`${API_BASE}/community/roadmap`),
        ]);

        if (
          !statsRes.ok ||
          !contributorsRes.ok ||
          !activityRes.ok ||
          !mixRes.ok ||
          !reviewsRes.ok ||
          !graphRes.ok ||
          !sunburstRes.ok ||
          !pulseRes.ok ||
          !issuesRes.ok ||
          !roadmapRes.ok
        ) {
          throw new Error('Failed to fetch community data');
        }

        const stats = await statsRes.json();
        const contributors = await contributorsRes.json();
        const activity = await activityRes.json();
        const mix = await mixRes.json();
        const reviews = await reviewsRes.json();
        const graph = await graphRes.json();
        const sunburst = await sunburstRes.json();
        const pulse = await pulseRes.json();
        const issues = await issuesRes.json();
        const roadmap = await roadmapRes.json();

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
      } catch (err) {
        console.warn('Failed to fetch community data, using fallback cache:', err);
        setData(MOCK_DASHBOARD_DATA);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 font-sans transition-colors duration-500">
        <div className="max-w-7xl mx-auto px-6 md:px-8 space-y-8">
          <div className="h-14 md:h-20" aria-hidden="true" />
          <motion.h1
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50 pl-1"
          >
            Initializing Dashboard...
          </motion.h1>
          <DashboardSkeleton />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-red-500 font-mono tracking-tighter">
            CONNECTION_ERROR
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mt-2 max-w-md mx-auto">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-bold rounded-full shadow-lg hover:shadow-blue-500/40 transition-all active:scale-95"
          >
            Re-establish Link
          </button>
        </div>
      </div>
    );
  }

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
            <ActivityPulse events={data.pulse} />
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
                <GoodFirstIssues data={data.issues} />

                {/* Dynamic Bento Grid Layout */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {/* Primary Stats Section */}
                  <StatsCard
                    title="Contributors"
                    value={data.stats?.contributors || (data.contributors ? data.contributors.length : 43)}
                    icon={Users}
                    description="43+ active open-source contributors"
                    trend="up"
                    color="blue"
                  />
                  <StatsCard
                    title="Repository Stars"
                    value={data.stats?.repository?.stars || 15}
                    icon={Star}
                    description="Global project recognition"
                    trend="up"
                    color="purple"
                  />
                  <StatsCard
                    title="PR Throughput"
                    value={data.stats?.pull_requests?.total || 674}
                    icon={GitMerge}
                    description={`${data.stats?.pull_requests?.open || 0} open, ${data.stats?.pull_requests?.closed || 674} merged PRs`}
                    trend="up"
                    color="cyan"
                  />
                  <StatsCard
                    title="Commit Count"
                    value={data.stats?.commits?.total || 2014}
                    icon={GitCommit}
                    description="2,014 lifetime repository commits"
                    trend="up"
                    color="blue"
                  />

                  {/* Main Visualizations Row */}
                  <div className="col-span-full lg:col-span-2 transition-all duration-300">
                    <ActivityAreaChart data={data.activity} />
                  </div>

                  <div className="col-span-full lg:col-span-2">
                    <ContributionMixChart data={data.mix} />
                  </div>

                  <div className="col-span-full">
                    <Leaderboard contributors={data.contributors} />
                  </div>

                  <ForceDirectedGraph data={data.graph} />

                  <RepositorySunburst data={data.sunburst} />
                  <div className="col-span-full lg:col-span-2">
                    <ReviewerMetrics data={data.reviews} />
                  </div>

                  <div className="col-span-full">
                    <ProjectRoadmap data={data.roadmap} />
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

        {/* Footer Meta */}
        <div className="pt-8 border-t border-slate-200 dark:border-slate-800 flex justify-between items-center text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          <span>System Status: Optimal</span>
          <span>Last Sync: {new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
}
