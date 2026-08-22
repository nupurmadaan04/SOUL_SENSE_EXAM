'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, ExternalLink, Sparkles, Tag } from 'lucide-react';
import { cn } from '@/lib/utils';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui';

interface Issue {
  id: number;
  number: number;
  title: string;
  html_url: string;
  labels: string[];
  created_at: string;
  comments_count: number;
  assignee?: string;
  assignee_avatar_url?: string;
  is_beginner: boolean;
}

interface GoodFirstIssuesProps {
  data: {
    issues: Issue[];
    show_notice: boolean;
  };
}

export function GoodFirstIssues({ data }: GoodFirstIssuesProps) {
  const { issues, show_notice } = data;
  const [currentIndex, setCurrentIndex] = useState(0);
  const [direction, setDirection] = useState(0); // -1 for left, 1 for right

  const handleNext = useCallback(() => {
    if (!issues) return;
    setDirection(1);
    setCurrentIndex((prev) => (prev + 1) % issues.length);
  }, [issues]);

  const handlePrev = useCallback(() => {
    if (!issues) return;
    setDirection(-1);
    setCurrentIndex((prev) => (prev - 1 + issues.length) % issues.length);
  }, [issues]);

  // Auto-rotate the carousel
  useEffect(() => {
    if (!issues || issues.length <= 1) return;

    const interval = setInterval(() => {
      handleNext();
    }, 5000); // 5 seconds per issue

    return () => clearInterval(interval);
  }, [currentIndex, issues, handleNext]);

  if (!issues || issues.length === 0) return null;

  const currentIssue = issues[currentIndex];

  const variants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 300 : -300,
      opacity: 0,
      scale: 0.9,
    }),
    center: {
      zIndex: 1,
      x: 0,
      opacity: 1,
      scale: 1,
    },
    exit: (direction: number) => ({
      zIndex: 0,
      x: direction < 0 ? 300 : -300,
      opacity: 0,
      scale: 0.9,
    }),
  };

  return (
    <div className="col-span-full relative bg-white/95 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200/90 dark:border-white/10 rounded-2xl p-6 overflow-hidden min-h-[160px] group transition-all duration-500 shadow-sm hover:shadow-md">
      <div className="relative z-10 flex flex-col h-full">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-xl">
              <Sparkles className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white leading-none">
                Priority Tasks
              </h3>
              {show_notice && (
                <p className="text-xs text-slate-600 dark:text-slate-400 font-medium mt-1">
                  Connect with the community by picking up a task.
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 self-end md:self-auto">
            <div className="px-3 py-1 bg-slate-100 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/5 text-[10px] font-bold text-slate-500 dark:text-slate-400 tabular-nums">
              {currentIndex + 1} / {issues.length}
            </div>
            <div className="flex gap-1">
              <button
                onClick={handlePrev}
                className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition-colors text-slate-500 hover:text-slate-900 dark:hover:text-white"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={handleNext}
                className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 transition-colors text-slate-500 hover:text-slate-900 dark:hover:text-white"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Carousel View */}
        <div className="flex-1 relative overflow-hidden flex items-center">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentIndex}
              custom={direction}
              variants={variants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{
                x: { type: 'tween', ease: 'easeOut', duration: 0.3 },
                opacity: { duration: 0.2 },
                scale: { duration: 0.4 },
              }}
              className="w-full"
            >
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-6">
                    <div className="space-y-2">
                      <h4 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white line-clamp-2 leading-snug">
                        {currentIssue.title}
                      </h4>
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono font-medium text-slate-500">
                          #{currentIssue.number}
                        </span>
                        {currentIssue.assignee ? (
                          <div className="flex items-center gap-2 px-2 py-0.5 bg-indigo-50 dark:bg-indigo-500/10 rounded-full border border-indigo-100 dark:border-indigo-500/20">
                            <Avatar className="h-4 w-4">
                              <AvatarImage src={currentIssue.assignee_avatar_url} />
                              <AvatarFallback className="text-[8px] bg-indigo-500 text-white">
                                {currentIssue.assignee.substring(0, 1).toUpperCase()}
                              </AvatarFallback>
                            </Avatar>
                            <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400">
                              {currentIssue.assignee}
                            </span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 dark:bg-emerald-500/10 rounded-full border border-emerald-100 dark:border-emerald-500/20">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                            <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                              Available
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                    <a
                      href={currentIssue.html_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0 p-2.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl hover:bg-blue-600 dark:hover:bg-blue-50 transition-all shadow-lg hover:scale-105 active:scale-95"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 pt-2">
                  {currentIssue.labels.map((label) => (
                    <span
                      key={label}
                      className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 rounded-md text-[10px] font-semibold text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                    >
                      {label}
                    </span>
                  ))}
                  {currentIssue.comments_count > 0 && (
                    <span className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 rounded-md text-[10px] font-semibold text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700 flex items-center gap-1">
                      {currentIssue.comments_count} comments
                    </span>
                  )}
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Progress dots (Glider) */}
        <div className="mt-6 flex justify-center gap-2 relative h-1.5">
          <div className="flex gap-2 relative">
            {issues.map((_, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setDirection(idx > currentIndex ? 1 : -1);
                  setCurrentIndex(idx);
                }}
                className="relative h-1.5 w-1.5 rounded-full bg-slate-200 dark:bg-white/10 outline-none transition-colors hover:bg-slate-300 dark:hover:bg-white/20"
              />
            ))}

            {/* The Glider */}
            <motion.div
              layoutId="good-first-issues-glider"
              className="absolute h-1.5 w-1.5 bg-blue-500 rounded-full z-10"
              initial={false}
              animate={{
                x: currentIndex * 14, // 6px (w-1.5) + 8px (gap-2) = 14px per step
              }}
              transition={{ type: 'tween', ease: 'easeOut', duration: 0.3 }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
