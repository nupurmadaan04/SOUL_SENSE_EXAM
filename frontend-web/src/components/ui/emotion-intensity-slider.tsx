'use client';

import React, { useMemo, useState, useEffect } from 'react';
import { motion, AnimatePresence, useSpring, useTransform } from 'framer-motion';
import { cn } from '@/lib/utils';

export interface EmotionIntensitySliderProps {
    value: number;
    onChange: (value: number) => void;
    min?: number;
    max?: number;
    step?: number;
    label?: string;
    showEmoji?: boolean;
    type?: 'mood' | 'energy' | 'stress' | 'generic';
    className?: string;
}

const configByType = {
    mood: [
        { value: 1, emoji: '😢', label: 'Very Sad', color: '#EF4444' }, // red-500
        { value: 3, emoji: '😕', label: 'Sad', color: '#F97316' }, // orange-500
        { value: 5, emoji: '😐', label: 'Neutral', color: '#EAB308' }, // yellow-500
        { value: 8, emoji: '🙂', label: 'Happy', color: '#84CC16' }, // lime-500
        { value: 10, emoji: '😄', label: 'Very Happy', color: '#22C55E' }, // green-500
    ],
    energy: [
        { value: 1, emoji: '😴', label: 'Exhausted', color: '#6366F1' }, // indigo-500
        { value: 3, emoji: '🥱', label: 'Tired', color: '#8B5CF6' }, // violet-500
        { value: 5, emoji: '😐', label: 'Normal', color: '#EAB308' }, // yellow-500
        { value: 8, emoji: '⚡', label: 'Energetic', color: '#F59E0B' }, // amber-500
        { value: 10, emoji: '🚀', label: 'Hyper', color: '#EF4444' }, // red-500
    ],
    stress: [
        { value: 1, emoji: '🧘', label: 'Calm', color: '#10B981' }, // emerald-500
        { value: 3, emoji: '😌', label: 'Relaxed', color: '#3B82F6' }, // blue-500
        { value: 5, emoji: '😐', label: 'Fine', color: '#EAB308' }, // yellow-500
        { value: 8, emoji: '😰', label: 'Stressed', color: '#F97316' }, // orange-500
        { value: 10, emoji: '🔥', label: 'Overwhelmed', color: '#EF4444' }, // red-500
    ],
    generic: [
        { value: 1, emoji: '⚪', label: 'Low', color: '#94A3B8' }, // slate-400
        { value: 5, emoji: '🔘', label: 'Medium', color: '#6366F1' }, // indigo-500
        { value: 10, emoji: '⚫', label: 'High', color: '#1E293B' }, // slate-800
    ],
};

export function EmotionIntensitySlider({
    value,
    onChange,
    min = 1,
    max = 10,
    step = 1,
    label,
    showEmoji = true,
    type = 'mood',
    className,
}: EmotionIntensitySliderProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [internalValue, setInternalValue] = useState(value);

    // Sync internal value with prop
    useEffect(() => {
        setInternalValue(value);
    }, [value]);

    const config = configByType[type] || configByType.generic;

    const currentStage = useMemo(() => {
        // Find the closest stage that is greater than or equal to current value
        const stage = config.slice().reverse().find((s) => internalValue >= s.value) || config[0];
        return stage;
    }, [internalValue, config]);

    // Spring animation for the thumb position
    const xPercentage = ((internalValue - min) / (max - min)) * 100;
    const springX = useSpring(xPercentage, { damping: 20, stiffness: 300 });

    useEffect(() => {
        springX.set(xPercentage);
    }, [xPercentage, springX]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newVal = parseInt(e.target.value);
        setInternalValue(newVal);
        onChange(newVal);
    };

    return (
        <div className={cn('w-full space-y-8 select-none', className)}>
            {/* Header section with Label and Value */}
            <div className="flex items-center justify-between">
                {label && (
                    <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-[0.2em]">
                        {label}
                    </h3>
                )}
                <div className="flex items-baseline gap-1">
                    <motion.span
                        key={internalValue}
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="text-3xl font-black tabular-nums"
                        style={{ color: currentStage.color }}
                    >
                        {internalValue}
                    </motion.span>
                    <span className="text-xs font-bold text-muted-foreground/50">/{max}</span>
                </div>
            </div>

            <div className="relative pt-12 pb-6 px-2">
                {/* Emoji Display section */}
                <AnimatePresence mode="wait">
                    {showEmoji && (
                        <motion.div
                            key={currentStage.emoji}
                            initial={{ y: 20, opacity: 0, scale: 0.5, rotate: -10 }}
                            animate={{ y: 0, opacity: 1, scale: 1, rotate: 0 }}
                            exit={{ y: -20, opacity: 0, scale: 0.5, rotate: 10 }}
                            transition={{ type: 'spring', damping: 15, stiffness: 200 }}
                            className="absolute -top-6 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 pointer-events-none"
                        >
                            <div
                                className="text-6xl drop-shadow-[0_10px_10px_rgba(0,0,0,0.1)] transition-transform duration-300"
                                style={{
                                    filter: isDragging ? `drop-shadow(0 0 20px ${currentStage.color}60)` : 'none',
                                    transform: isDragging ? 'scale(1.1)' : 'scale(1)'
                                }}
                            >
                                {currentStage.emoji}
                            </div>
                            <motion.span
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="text-sm font-black whitespace-nowrap px-3 py-1 rounded-full"
                                style={{
                                    backgroundColor: `${currentStage.color}15`,
                                    color: currentStage.color
                                }}
                            >
                                {currentStage.label}
                            </motion.span>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* The Slider Track Container */}
                <div className="relative h-12 flex items-center">
                    {/* Main Track Background */}
                    <div className="absolute inset-0 h-4 my-auto w-full bg-secondary/30 backdrop-blur-sm rounded-full overflow-hidden shadow-inner">
                        {/* Active Gradient Track */}
                        <motion.div
                            className="absolute h-full left-0 top-0 rounded-full"
                            style={{
                                width: `${xPercentage}%`,
                                background: `linear-gradient(90deg, ${currentStage.color}80 0%, ${currentStage.color} 100%)`,
                                boxShadow: `0 0 15px ${currentStage.color}40`
                            }}
                            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                        />
                    </div>

                    {/* Tick Marks */}
                    <div className="absolute inset-0 h-4 my-auto w-full flex justify-between items-center px-[2px] pointer-events-none">
                        {Array.from({ length: max - min + 1 }).map((_, i) => {
                            const val = min + i;
                            const isActive = val <= internalValue;
                            return (
                                <div
                                    key={i}
                                    className={cn(
                                        "w-1 h-1 rounded-full transition-all duration-500",
                                        isActive ? "bg-white/50 scale-125" : "bg-foreground/10"
                                    )}
                                />
                            );
                        })}
                    </div>

                    {/* Hidden Input for handling events */}
                    <input
                        type="range"
                        min={min}
                        max={max}
                        step={step}
                        value={internalValue}
                        onChange={handleInputChange}
                        onMouseDown={() => setIsDragging(true)}
                        onMouseUp={() => setIsDragging(false)}
                        onTouchStart={() => setIsDragging(true)}
                        onTouchEnd={() => setIsDragging(false)}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-30"
                    />

                    {/* Visual Thumb */}
                    <motion.div
                        className="absolute h-8 w-8 rounded-full z-20 pointer-events-none flex items-center justify-center"
                        style={{
                            left: `calc(${xPercentage}% - 16px)`,
                            backgroundColor: 'white',
                            boxShadow: `0 4px 10px rgba(0,0,0,0.1), 0 0 20px ${currentStage.color}40`,
                            border: `3px solid ${currentStage.color}`
                        }}
                        animate={{
                            scale: isDragging ? 1.2 : 1,
                            y: isDragging ? -2 : 0
                        }}
                    >
                        <div
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: currentStage.color }}
                        />
                        {/* Thumb Glow Effect */}
                        <motion.div
                            className="absolute inset-0 rounded-full"
                            animate={{
                                boxShadow: isDragging
                                    ? [`0 0 20px ${currentStage.color}40`, `0 0 40px ${currentStage.color}60`, `0 0 20px ${currentStage.color}40`]
                                    : `0 0 10px ${currentStage.color}00`
                            }}
                            transition={{ repeat: Infinity, duration: 1.5 }}
                        />
                    </motion.div>
                </div>

                {/* Min/Max Labels at the bottom */}
                <div className="flex justify-between items-center mt-2 px-1 text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">
                    <span>{config[0].label}</span>
                    <span>{config[config.length - 1].label}</span>
                </div>
            </div>
        </div>
    );
}
