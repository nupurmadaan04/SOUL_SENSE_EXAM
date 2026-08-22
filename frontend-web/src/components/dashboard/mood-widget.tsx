'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Frown, Meh, Smile, Sparkles, Heart } from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import { toast } from '@/lib/toast';

const MOODS = [
  {
    icon: Frown,
    label: 'Low',
    rating: 1,
    colorClass: 'text-rose-500 bg-rose-500/10 border-rose-500/30 hover:bg-rose-500/20',
  },
  {
    icon: Meh,
    label: 'Moderate',
    rating: 2,
    colorClass: 'text-amber-500 bg-amber-500/10 border-amber-500/30 hover:bg-amber-500/20',
  },
  {
    icon: Smile,
    label: 'Good',
    rating: 3,
    colorClass: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30 hover:bg-emerald-500/20',
  },
  {
    icon: Sparkles,
    label: 'Great',
    rating: 4,
    colorClass: 'text-purple-500 bg-purple-500/10 border-purple-500/30 hover:bg-purple-500/20',
  },
];

const DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Today'];

export const MoodWidget = () => {
  const [loggedMood, setLoggedMood] = useState<number | null>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('soulsense_today_mood');
      return saved ? parseInt(saved, 10) : null;
    }
    return null;
  });

  const handleMoodSelect = (rating: number) => {
    setLoggedMood(rating);
    try {
      localStorage.setItem('soulsense_today_mood', String(rating));
    } catch (e) {}
    const mood = MOODS.find((m) => m.rating === rating);
    toast.success(`Logged your mood: ${mood?.label || 'Recorded'}`);
  };

  const selectedMood = MOODS.find((m) => m.rating === loggedMood);

  return (
    <div className="border border-border/80 bg-card/90 backdrop-blur-md rounded-3xl p-6 shadow-xl flex flex-col justify-between h-full group overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between pb-2">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-2xl bg-primary/10 text-primary">
            <Heart className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-foreground">Daily Mood Check-in</h3>
            <p className="text-[11px] text-muted-foreground">How is your emotional energy right now?</p>
          </div>
        </div>
        {loggedMood && (
          <button
            onClick={() => setLoggedMood(null)}
            className="text-[10px] text-primary font-bold hover:underline cursor-pointer"
          >
            Change
          </button>
        )}
      </div>

      {/* Mood Selector Buttons */}
      <div className="my-auto py-2">
        <AnimatePresence mode="wait">
          {!loggedMood ? (
            <motion.div
              key="selector"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="grid grid-cols-4 gap-2"
            >
              {MOODS.map((mood) => {
                const Icon = mood.icon;
                return (
                  <button
                    key={mood.rating}
                    onClick={() => handleMoodSelect(mood.rating)}
                    className={cn(
                      'flex flex-col items-center justify-center p-2.5 rounded-2xl border transition-all duration-200 cursor-pointer shadow-sm hover:scale-105 active:scale-95 text-center',
                      mood.colorClass
                    )}
                    title={mood.label}
                  >
                    <Icon className="w-6 h-6 mb-1.5 shrink-0" strokeWidth={2} />
                    <span className="text-[11px] font-bold tracking-tight whitespace-nowrap">{mood.label}</span>
                  </button>
                );
              })}
            </motion.div>
          ) : (
            <motion.div
              key="logged"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center justify-between p-3.5 rounded-2xl bg-muted/30 border border-border/60"
            >
              <div className="flex items-center gap-3">
                {selectedMood && (
                  <div className={cn('p-2.5 rounded-xl border shadow-sm', selectedMood.colorClass)}>
                    <selectedMood.icon className="w-5 h-5" strokeWidth={2} />
                  </div>
                )}
                <div>
                  <p className="text-xs font-bold text-foreground">Mood Logged: {selectedMood?.label}</p>
                  <p className="text-[10px] text-muted-foreground">Recorded for your daily emotional tracking</p>
                </div>
              </div>
              <Link
                href="/journal"
                className="inline-flex items-center gap-1 text-[11px] font-bold text-primary hover:text-primary/80 transition-colors bg-primary/10 px-3 py-1.5 rounded-xl"
              >
                Journal
                <ArrowRight className="h-3 w-3" />
              </Link>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Past 7 Days Mood Trend */}
      <div className="pt-3 border-t border-border/40">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Past 7 Days History</span>
          <span className="text-[9px] font-medium text-muted-foreground/80">
            {loggedMood ? `Today: ${selectedMood?.label}` : 'No mood logged today'}
          </span>
        </div>
        <div className="grid grid-cols-7 gap-1.5">
          {DAYS_OF_WEEK.map((dayName, i) => {
            const isToday = i === 6;
            const moodObj = isToday && loggedMood ? MOODS.find((m) => m.rating === loggedMood) : null;

            return (
              <div
                key={i}
                className="flex flex-col items-center gap-1 group/day"
                title={moodObj ? `${dayName}: ${moodObj.label}` : `${dayName}: No entry`}
              >
                {moodObj ? (
                  <div
                    className={cn(
                      'w-full h-3 rounded-full transition-all duration-300 shadow-xs',
                      moodObj.rating === 1 && 'bg-rose-500',
                      moodObj.rating === 2 && 'bg-amber-500',
                      moodObj.rating === 3 && 'bg-emerald-500',
                      moodObj.rating === 4 && 'bg-purple-500'
                    )}
                  />
                ) : (
                  <div className="w-full h-3 rounded-full border border-dashed border-border/60 bg-muted/10 flex items-center justify-center">
                    <span className="text-[7px] text-muted-foreground/40 leading-none">—</span>
                  </div>
                )}
                <span
                  className={cn(
                    'text-[8px] font-bold',
                    isToday ? 'text-primary' : 'text-muted-foreground/70'
                  )}
                >
                  {dayName}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
