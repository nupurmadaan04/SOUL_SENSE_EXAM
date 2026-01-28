'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  BentoGrid,
  StatsCard,
  ActivityAreaChart,
  ContributionMixChart,
  DashboardSkeleton,
  Leaderboard,
  ContributionHeatmap,
  ReviewerMetrics,
} from '@/components/dashboard';
import { Users, GitMerge, Star, GitCommit } from 'lucide-react';
import { motion } from 'framer-motion';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsRes, contributorsRes, activityRes, mixRes, reviewsRes, graphRes, sunburstRes] =
          await Promise.all([
            fetch('/api/v1/community/stats'),
            fetch('/api/v1/community/contributors?limit=20'),
            fetch('/api/v1/community/activity'),
            fetch('/api/v1/community/mix'),
            fetch('/api/v1/community/reviews'),
            fetch('/api/v1/community/graph'),
            fetch('/api/v1/community/sunburst'),
          ]);

        if (
          !statsRes.ok ||
          !contributorsRes.ok ||
          !activityRes.ok ||
          !mixRes.ok ||
          !reviewsRes.ok ||
          !graphRes.ok ||
          !sunburstRes.ok
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

        setData({ stats, contributors, activity, mix, reviews, graph, sunburst });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-8">
        <div className="max-w-7xl mx-auto space-y-8">
          <motion.h1
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-4xl font-bold tracking-tight text-slate-900 dark:text-slate-50"
          >
            Community Pulse
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
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-6 md:p-8 font-sans transition-colors duration-500">
      <div className="max-w-7xl mx-auto space-y-12">
        {/* Header Section */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6"
        >
          <div className="space-y-2">
            <h1 className="text-5xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-sky-600 via-blue-600 to-indigo-600 dark:from-sky-400 dark:via-blue-400 dark:to-indigo-400 drop-shadow-sm">
              COMMUNITY_PULSE
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-lg font-medium max-w-xl">
              Analyzing velocity, sentiment, and impact across the{' '}
              <span className="text-blue-500 font-bold">SoulSense</span> open source ecosystem in
              real-time.
            </p>
          </div>
          <motion.a
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            href="https://github.com/nupurmadaan04/SOUL_SENSE_EXAM/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22"
            target="_blank"
            className="group px-8 py-4 bg-slate-950 dark:bg-white text-white dark:text-slate-950 font-black rounded-2xl shadow-2xl flex items-center gap-2 transition-all overflow-hidden relative border border-transparent hover:border-blue-500/20 dark:hover:border-blue-400/20"
          >
            <span className="relative z-10 group-hover:scale-105 transition-transform duration-300">
              CONTRIBUTE_NOW
            </span>
            <span className="relative z-10 group-hover:rotate-12 transition-transform duration-300">
              ✨
            </span>
            <div className="absolute inset-0 bg-blue-500/10 dark:bg-blue-400/10 backdrop-blur-md opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </motion.a>
        </motion.div>

        {/* Dynamic Bento Grid Layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Primary Stats Section */}
          <StatsCard
            title="Contributors"
            value={data.contributors.length}
            icon={Users}
            description="Unique collaborators this year"
            trend="up"
            color="blue"
          />
          <StatsCard
            title="Repository Stars"
            value={data.stats.repository.stars}
            icon={Star}
            description="Global project recognition"
            trend="up"
            color="purple"
          />
          <StatsCard
            title="PR Throughput"
            value={data.stats.pull_requests.total}
            icon={GitMerge}
            description={`${data.stats.pull_requests.open} open discussions`}
            trend="neutral"
            color="cyan"
          />
          <StatsCard
            title="Commit Count"
            value={data.mix.find((m: any) => m.name === 'Core Features')?.count || 0}
            icon={GitCommit}
            description="Lifetime engineering velocity"
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

          <ReviewerMetrics data={data.reviews} />
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
