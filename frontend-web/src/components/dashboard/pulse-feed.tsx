'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Image from 'next/image';
import {
  GitCommit,
  GitPullRequest,
  AlertCircle,
  MessageSquare,
  Star,
  GitFork,
  User,
  ChevronDown,
} from 'lucide-react';

interface PulseEvent {
  user: string;
  action: string;
  time: string;
  type: string;
  avatar?: string;
}

export function ActivityPulse({ events = [] }: { events: PulseEvent[] }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);

  useEffect(() => {
    if (events.length === 0 || isHovered) return;

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % events.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [events, isHovered]);

  const getIcon = (type: string) => {
    switch (type) {
      case 'push':
        return <GitCommit className="w-3 h-3 text-blue-500" />;
      case 'pr':
        return <GitPullRequest className="w-3 h-3 text-purple-500" />;
      case 'issue':
        return <AlertCircle className="w-3 h-3 text-orange-500" />;
      case 'comment':
        return <MessageSquare className="w-3 h-3 text-cyan-500" />;
      case 'star':
        return <Star className="w-3 h-3 text-yellow-500" />;
      case 'fork':
        return <GitFork className="w-3 h-3 text-emerald-500" />;
      default:
        return <User className="w-3 h-3 text-slate-400" />;
    }
  };

  const getTimeAgo = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.round(diffMs / 60000);

      if (diffMins < 1) return 'now';
      if (diffMins < 60) return `${diffMins}m`;
      if (diffMins < 1440) return `${Math.round(diffMins / 60)}h`;
      return `${Math.round(diffMins / 1440)}d`;
    } catch (e) {
      return '';
    }
  };

  if (events.length === 0) return null;

  const currentEvent = events[currentIndex];

  return (
    <div
      className="relative z-50 inline-block group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Pill-Styled Box (Matches Image Layout) */}
      <div className="flex items-center h-8 bg-white/95 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200/90 dark:border-white/10 rounded-full overflow-hidden shadow-sm transition-all group-hover:border-blue-500/40 group-hover:shadow-md cursor-pointer w-[340px]">
        {/* Left Side: Avatar + Action (Ticker) */}
        <div className="flex items-center gap-2 pl-2 pr-3 flex-grow min-w-0 h-full transition-colors">
          <div className="flex-shrink-0">
            {currentEvent.avatar ? (
              <Image
                src={currentEvent.avatar}
                alt={currentEvent.user}
                width={20}
                height={20}
                className="w-5 h-5 rounded-full border border-white/20"
              />
            ) : (
              <div className="w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center border border-slate-200 dark:border-white/10">
                <User className="w-3 h-3 text-slate-400" />
              </div>
            )}
          </div>
          <div className="flex-grow min-w-0 flex items-center gap-1.5 overflow-hidden h-full">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentIndex}
                initial={{ x: 10, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: -10, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="flex items-center gap-1.5 whitespace-nowrap overflow-hidden w-full"
              >
                <span className="text-[10px] font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider shrink-0 max-w-[80px] truncate">
                  {currentEvent.user}
                </span>
                <span className="text-[10px] font-normal text-slate-500 dark:text-slate-400 truncate flex-grow">
                  {currentEvent.action}
                </span>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {/* Vertical Divider */}
        <div className="h-4 w-[1px] bg-slate-200 dark:bg-white/10 flex-shrink-0" />

        {/* Right Side: Blinking Dot + Status */}
        <div className="flex items-center gap-2 px-3 h-full hover:bg-slate-50 dark:hover:bg-white/5 transition-colors flex-shrink-0">
          <div className="relative">
            <div
              className={`w-1.5 h-1.5 rounded-full animate-pulse ${currentEvent.type === 'system' ? 'bg-orange-500' : 'bg-emerald-500'}`}
            />
            <div
              className={`absolute inset-0 w-1.5 h-1.5 rounded-full animate-ping opacity-75 ${currentEvent.type === 'system' ? 'bg-orange-500' : 'bg-emerald-500'}`}
            />
          </div>
          <span className="text-[9px] font-mono font-medium text-slate-500 dark:text-slate-500 tracking-tight">
            {currentEvent.type === 'system' ? 'STANDBY' : `LIVE_${getTimeAgo(currentEvent.time)}`}
          </span>
          <ChevronDown
            className={`w-3 h-3 text-slate-400 transition-transform duration-300 ${isHovered ? 'rotate-180' : ''}`}
          />
        </div>
      </div>

      {/* Hover Dropdown History (Matches refined theme) */}
      <AnimatePresence>
        {isHovered && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 4, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            className="absolute top-full left-0 mt-1 min-w-[320px] bg-white/95 dark:bg-slate-950/95 backdrop-blur-2xl border border-slate-200 dark:border-white/10 rounded-2xl shadow-2xl overflow-hidden"
          >
            <div className="px-4 py-2 bg-slate-50/50 dark:bg-white/5 flex items-center justify-between border-b border-slate-100 dark:border-white/5">
              <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.15em]">
                System Activity Log
              </span>
              <div className="flex items-center gap-1.5">
                <div className="w-1 h-1 bg-emerald-500 rounded-full animate-pulse" />
                <span className="text-[8px] font-mono text-emerald-600 dark:text-emerald-500 font-bold uppercase tracking-wider">
                  Syncing
                </span>
              </div>
            </div>
            <div className="max-h-72 overflow-y-auto custom-scrollbar">
              {events.map((event, idx) => (
                <div
                  key={idx}
                  className={`flex items-start gap-3 px-4 py-3 transition-colors hover:bg-slate-100/50 dark:hover:bg-white/5 border-b border-slate-100 dark:border-white/5 last:border-0 ${idx === currentIndex ? 'border-l-2 border-l-blue-500 bg-blue-500/5' : ''}`}
                >
                  <div className="flex-shrink-0 mt-0.5 relative">
                    {event.avatar ? (
                      <Image
                        src={event.avatar}
                        alt={event.user}
                        width={28}
                        height={28}
                        className="w-7 h-7 rounded-full border border-slate-200 dark:border-white/10"
                      />
                    ) : (
                      <div className="w-7 h-7 rounded-full bg-slate-200 dark:bg-slate-800 flex items-center justify-center border border-slate-300 dark:border-white/10">
                        <User className="w-4 h-4 text-slate-400" />
                      </div>
                    )}
                    <div className="absolute -bottom-1 -right-1 bg-white dark:bg-slate-900 rounded-full p-0.5 border border-slate-100 dark:border-white/5">
                      {getIcon(event.type)}
                    </div>
                  </div>
                  <div className="flex-grow min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-[11px] font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wide">
                        {event.user}
                      </span>
                      <span className="text-[9px] font-mono text-slate-400 uppercase">
                        {getTimeAgo(event.time)}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-tight font-normal">
                      {event.action}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
