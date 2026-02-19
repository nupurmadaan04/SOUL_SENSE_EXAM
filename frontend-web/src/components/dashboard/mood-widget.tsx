'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BentoGridItem } from './bento-grid';
import { History, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';

const EMOJIS = [
    { char: '😢', label: 'Very Low', rating: 1, color: 'text-red-500 bg-red-500/10' },
    { char: '😕', label: 'Low', rating: 2, color: 'text-orange-500 bg-orange-500/10' },
    { char: '😐', label: 'Neutral', rating: 3, color: 'text-yellow-500 bg-yellow-500/10' },
    { char: '🙂', label: 'Good', rating: 4, color: 'text-blue-500 bg-blue-500/10' },
    { char: '😄', label: 'Great', rating: 5, color: 'text-green-500 bg-green-500/10' },
];

export const MoodWidget = () => {
    const [loggedMood, setLoggedMood] = useState<number | null>(null);

    // Mock trend data for last 7 days (1-5 scale)
    const trendData = [3, 4, 3, 5, 4, 2, 4];

    const handleMoodSelect = (rating: number) => {
        // Simulate logging
        setLoggedMood(rating);
    };

    const selectedEmoji = EMOJIS.find(e => e.rating === loggedMood);

    return (
        <BentoGridItem
            title="Daily Check-in"
            description={loggedMood ? "Good to know how you're feeling." : "How are you feeling right now?"}
            className="md:col-span-1 border-none shadow-none p-0 group overflow-hidden"
        >
            <div className="flex flex-col h-full bg-white/60 dark:bg-black/40 backdrop-blur-xl rounded-3xl p-6 border border-white/20 transition-all group-hover:shadow-2xl">
                <div className="flex-1 flex flex-col justify-center">
                    <AnimatePresence mode="wait">
                        {!loggedMood ? (
                            <motion.div
                                key="selector"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -10 }}
                                className="flex justify-between items-center gap-2"
                            >
                                {EMOJIS.map((mood) => (
                                    <motion.button
                                        key={mood.rating}
                                        whileHover={{ scale: 1.2, y: -5 }}
                                        whileTap={{ scale: 0.9 }}
                                        onClick={() => handleMoodSelect(mood.rating)}
                                        className={cn(
                                            "flex-1 aspect-square rounded-2xl flex items-center justify-center text-2xl transition-all border border-transparent hover:border-white/40 shadow-sm",
                                            "bg-neutral-100/50 dark:bg-neutral-800/50 hover:bg-white dark:hover:bg-neutral-700"
                                        )}
                                        title={mood.label}
                                    >
                                        {mood.char}
                                    </motion.button>
                                ))}
                            </motion.div>
                        ) : (
                            <motion.div
                                key="logged"
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="flex flex-col items-center py-4"
                            >
                                <div className="text-6xl mb-3 drop-shadow-xl">{selectedEmoji?.char}</div>
                                <div className={cn(
                                    "px-4 py-1 rounded-full text-xs font-bold border mb-4",
                                    selectedEmoji?.color,
                                    "border-current/20"
                                )}>
                                    {selectedEmoji?.label}
                                </div>
                                <Link
                                    href="/journal"
                                    className="group/link flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 font-semibold hover:underline"
                                >
                                    Complete Journal
                                    <ArrowRight className="h-3.5 w-3.5 group-hover/link:translate-x-1 transition-transform" />
                                </Link>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Mini Trend */}
                <div className="mt-6 pt-4 border-t border-neutral-200/50 dark:border-neutral-800/50">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] uppercase tracking-wider font-bold text-neutral-400">Past 7 Days</span>
                        <History className="h-3 w-3 text-neutral-400" />
                    </div>
                    <div className="flex items-end justify-between h-8 gap-1 px-1">
                        {trendData.map((val, i) => (
                            <motion.div
                                key={i}
                                initial={{ height: 0 }}
                                animate={{ height: `${(val / 5) * 100}%` }}
                                className={cn(
                                    "flex-1 rounded-full min-h-[4px]",
                                    val >= 4 ? "bg-green-500/40" : val <= 2 ? "bg-red-500/40" : "bg-yellow-500/40"
                                )}
                            />
                        ))}
                    </div>
                </div>
            </div>
        </BentoGridItem>
import { BentoGridItem } from './bento-grid';
import { Smile, Frown, Meh } from 'lucide-react';

export const MoodWidget = () => {
    // Mock data for now
    const moodRating = 8;
    const moodText = "Feeling Positive";

    const getMoodIcon = (rating: number) => {
        if (rating >= 7) return <Smile className="h-4 w-4" />;
        if (rating <= 4) return <Frown className="h-4 w-4" />;
        return <Meh className="h-4 w-4" />;
    };

    return (
        <BentoGridItem
            title="Today's Mood"
            description={`You rated your mood as ${moodRating}/10 today.`}
            header={
                <div className="flex flex-col items-center justify-center h-full min-h-[6rem] bg-gradient-to-br from-green-500/10 to-blue-500/10 rounded-xl">
                    <div className="text-4xl font-bold text-green-600 dark:text-green-400">{moodRating}</div>
                    <p className="text-sm font-medium mt-2">{moodText}</p>
                </div>
            }
            icon={getMoodIcon(moodRating)}
            className="md:col-span-1"
        />
    );
};
