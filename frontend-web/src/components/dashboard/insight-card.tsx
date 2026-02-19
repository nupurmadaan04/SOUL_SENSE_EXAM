'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Lightbulb,
    BarChart2,
    Target,
    AlertTriangle,
    X,
    ArrowRight,
    ShieldCheck
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

export type InsightType = 'tip' | 'pattern' | 'goal' | 'alert';

export interface Insight {
    id?: string;
    title: string;
    content: string;
    type: InsightType;
    actionLabel?: string;
}

interface InsightCardProps {
    insight: Insight;
    onDismiss?: (id?: string) => void;
    onAction?: (insight: Insight) => void;
    className?: string;
}

const typeConfigs: Record<string, {
    icon: any;
    colorClass: string;
    accentColor: string;
    label: string;
    textMainColor?: string;
}> = {
    tip: {
        icon: Lightbulb,
        colorClass: 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20',
        accentColor: 'from-yellow-400/20 to-orange-500/20',
        label: 'Tip',
        textMainColor: 'text-yellow-600 dark:text-yellow-400'
    },
    pattern: {
        icon: BarChart2,
        colorClass: 'text-blue-500 bg-blue-500/10 border-blue-500/20',
        accentColor: 'from-blue-400/20 to-indigo-500/20',
        label: 'Pattern',
        textMainColor: 'text-blue-600 dark:text-blue-400'
    },
    goal: {
        icon: Target,
        colorClass: 'text-purple-500 bg-purple-500/10 border-purple-500/20',
        accentColor: 'from-purple-400/20 to-pink-500/20',
        label: 'Goal',
        textMainColor: 'text-purple-600 dark:text-purple-400'
    },
    alert: {
        icon: AlertTriangle,
        colorClass: 'text-red-500 bg-red-500/10 border-red-500/20',
        accentColor: 'from-red-400/20 to-orange-500/20',
        label: 'Alert',
        textMainColor: 'text-red-600 dark:text-red-400'
    },
    safety: {
        icon: ShieldCheck,
        colorClass: 'text-green-500 bg-green-500/10 border-green-500/20',
        accentColor: 'from-green-400/20 to-emerald-500/20',
        label: 'Safety',
        textMainColor: 'text-green-600 dark:text-green-400'
    }
};

export const InsightCard = ({
    insight,
    onDismiss,
    onAction,
    className
}: InsightCardProps) => {
    const config = typeConfigs[insight.type];
    const Icon = config.icon;

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            className={cn(
                'group relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-6 shadow-xl backdrop-blur-xl transition-all dark:bg-black/40',
                'flex flex-col h-full justify-between',
                className
            )}
        >
            {/* Background Accent Glow */}
            <div className={cn(
                "absolute -inset-px bg-gradient-to-br opacity-0 transition-opacity duration-500 group-hover:opacity-10",
                config.accentColor
            )} />

            {/* Header with Type Icon and Dismiss Button */}
            <div className="relative z-10 mb-4 flex items-start justify-between">
                <div className={cn(
                    "flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold border",
                    config.colorClass
                )}>
                    <Icon className="h-3.5 w-3.5" />
                    <span>{config.label}</span>
                </div>

                {onDismiss && (
                    <button
                        onClick={() => onDismiss(insight.id)}
                        className="rounded-full p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 dark:hover:bg-neutral-800 dark:hover:text-neutral-200 transition-colors"
                    >
                        <X className="h-4 w-4" />
                    </button>
                )}
            </div>

            {/* Content */}
            <div className="relative z-10 flex-1">
                <h3 className="mb-2 text-lg font-bold text-neutral-800 dark:text-neutral-100">
                    {insight.title}
                </h3>
                <p className="text-sm leading-relaxed text-neutral-600 dark:text-neutral-400">
                    {insight.content}
                </p>
            </div>

            {/* Action Footer */}
            {onAction && (
                <div className="relative z-10 mt-6 pt-4 border-t border-neutral-100 dark:border-neutral-800">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onAction(insight)}
                        className={cn(
                            "p-0 h-auto font-semibold hover:bg-transparent hover:translate-x-1 transition-transform",
                            config.textMainColor || "text-blue-600 dark:text-blue-400"
                        )}
                    >
                        {insight.actionLabel || 'Learn more'}
                        <ArrowRight className="ml-1 h-3.5 w-3.5" />
                    </Button>
                </div>
            )}
        </motion.div>
import { BentoGridItem } from './bento-grid';
import { Lightbulb, TrendingUp, ShieldCheck } from 'lucide-react';

interface InsightCardProps {
    title: string;
    description: string;
    type: 'tip' | 'trend' | 'safety';
    className?: string;
}

export const InsightCard = ({ title, description, type, className }: InsightCardProps) => {
    const getIcon = () => {
        switch (type) {
            case 'tip': return <Lightbulb className="h-4 w-4" />;
            case 'trend': return <TrendingUp className="h-4 w-4" />;
            case 'safety': return <ShieldCheck className="h-4 w-4" />;
        }
    };

    const getColorClass = () => {
        switch (type) {
            case 'tip': return 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400';
            case 'trend': return 'bg-blue-500/10 text-blue-600 dark:text-blue-400';
            case 'safety': return 'bg-green-500/10 text-green-600 dark:text-green-400';
        }
    };

    return (
        <BentoGridItem
            title={title}
            description={description}
            header={
                <div className={`flex flex-1 w-full h-full min-h-[6rem] rounded-xl items-center justify-center ${getColorClass()} bg-opacity-10 border border-white/10`}>
                    {getIcon()}
                </div>
            }
            icon={getIcon()}
            className={className}
        />
    );
};
