'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Calendar, CheckCircle2, Circle, Clock, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Milestone {
  id: number;
  number: number;
  title: string;
  description: string;
  status: 'completed' | 'in-progress' | 'planned';
  progress: number;
  open_issues: number;
  closed_issues: number;
  due_on: string | null;
  html_url: string;
}

export function ProjectRoadmap({ data }: { data?: Milestone[] }) {
  const [milestones, setMilestones] = useState<Milestone[]>(data || []);
  const [loading, setLoading] = useState(!data);

  useEffect(() => {
    if (data) {
      setMilestones(data);
      setLoading(false);
      return;
    }

    async function fetchRoadmap() {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/v1/community/roadmap');
        const fetchedData = await res.json();
        setMilestones(fetchedData);
      } catch (err) {
        console.error('Failed to fetch roadmap:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchRoadmap();
  }, [data]);

  if (loading) {
    return (
      <div className="bg-white/40 dark:bg-slate-900/40 backdrop-blur-xl border border-slate-200/50 dark:border-white/10 rounded-2xl p-6 h-[300px] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-sky-500/20 border-t-sky-500 rounded-full animate-spin" />
          <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">
            Loading Roadmap...
          </span>
        </div>
      </div>
    );
  }

  if (!milestones || milestones.length === 0) {
    return (
      <div className="bg-white/40 dark:bg-slate-900/40 backdrop-blur-xl border border-slate-200/50 dark:border-white/10 rounded-2xl p-8 text-center">
        <TrendingUp className="w-12 h-12 text-slate-300 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
          Project Foundation Phase
        </h3>
        <p className="text-sm text-slate-500">
          We&apos;re currently establishing the core project structure. Check back soon for detailed
          milestones!
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white/60 dark:bg-slate-900/60 backdrop-blur-xl border border-slate-200 dark:border-white/5 rounded-2xl p-6 overflow-hidden shadow-sm hover:shadow-md transition-all">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-sky-500/10 rounded-lg">
            <TrendingUp className="w-5 h-5 text-sky-600 dark:text-sky-400" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white leading-none">
              Project Roadmap
            </h3>
            <span className="text-[10px] font-semibold text-slate-500">
              Future Milestones & Tracking
            </span>
          </div>
        </div>
      </div>

      <div className="relative">
        {/* Timeline Line */}
        <div className="absolute left-4 top-0 bottom-0 w-px bg-slate-200 dark:bg-slate-800" />

        <div className="space-y-8 relative">
          {milestones.map((milestone, idx) => (
            <motion.div
              key={milestone.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="relative pl-12"
            >
              {/* Timeline Node */}
              <div
                className={cn(
                  'absolute left-0 top-1 w-8 h-8 rounded-full border-[3px] flex items-center justify-center z-10 bg-white dark:bg-slate-900',
                  milestone.status === 'completed'
                    ? 'border-emerald-500 text-emerald-500'
                    : milestone.status === 'in-progress'
                      ? 'border-sky-500 text-sky-500'
                      : 'border-slate-200 dark:border-slate-700 text-slate-300'
                )}
              >
                {milestone.status === 'completed' ? (
                  <CheckCircle2 className="w-4 h-4 fill-current" />
                ) : milestone.status === 'in-progress' ? (
                  <Clock className="w-4 h-4" />
                ) : (
                  <Circle className="w-4 h-4" />
                )}
              </div>

              <div className="group relative">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <h4 className="font-bold text-slate-900 dark:text-white group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">
                      {milestone.title}
                    </h4>
                    {milestone.due_on && (
                      <div className="flex items-center gap-1.5 mt-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        <Calendar className="w-3 h-3" />
                        Target: {new Date(milestone.due_on).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                  <div
                    className={cn(
                      'px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-widest',
                      milestone.status === 'completed'
                        ? 'bg-emerald-50 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                        : milestone.status === 'in-progress'
                          ? 'bg-sky-50 bg-sky-500/10 text-sky-600 dark:text-sky-400'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                    )}
                  >
                    {milestone.status}
                  </div>
                </div>

                {milestone.description && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mb-3">
                    {milestone.description}
                  </p>
                )}

                <div className="space-y-2">
                  <div className="flex justify-between text-[10px] font-bold text-slate-400">
                    <span>PROGRESS</span>
                    <span>{milestone.progress}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${milestone.progress}%` }}
                      transition={{ duration: 1, ease: 'easeOut' }}
                      className={cn(
                        'h-full rounded-full',
                        milestone.status === 'completed' ? 'bg-emerald-500' : 'bg-sky-500'
                      )}
                    />
                  </div>
                </div>

                <div className="mt-3 flex items-center gap-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  <span>{milestone.closed_issues} Closed</span>
                  <span>{milestone.open_issues} Open</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
