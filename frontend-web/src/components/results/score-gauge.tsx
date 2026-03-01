"use client";

import React, { useEffect, useState } from "react";
import { motion, animate, useMotionValue, useTransform, useMotionValueEvent } from "framer-motion";
import { cn } from "@/lib/utils";

interface ScoreGaugeProps {
    score: number;
    size?: "sm" | "md" | "lg";
    showLabel?: boolean;
    animated?: boolean;
    label?: string;
    className?: string;
}

const ScoreGauge = ({
    score = 0,
    size = "md",
    showLabel = true,
    animated = true,
    label = "Your EQ Score",
    className,
}: ScoreGaugeProps) => {
    const [displayScore, setDisplayScore] = useState(0);
    const count = useMotionValue(0);
    const rounded = useTransform(count, (latest) => Math.round(latest));

    useEffect(() => {
        if (animated) {
            const controls = animate(count, score, {
                duration: 2,
                ease: "easeOut",
            });
            return () => controls.stop();
        } else {
            count.set(score);
        }
    }, [score, animated, count]);

    // Subscribe to motion value to update state for the score number
    useMotionValueEvent(rounded, "change", (latest: number) => {
        setDisplayScore(latest);
    });

    const getScoreColor = (value: number) => {
        if (value >= 90) return "stroke-indigo-600 text-indigo-600";
        if (value >= 80) return "stroke-emerald-500 text-emerald-500";
        return "stroke-red-500 text-red-500";
    };

    const getScoreGradient = (value: number) => {
        if (value >= 90) return "url(#gradient-indigo)";
        if (value >= 80) return "url(#gradient-emerald)";
        return "url(#gradient-red)";
    };

    const dimensions = {
        sm: { size: 80, stroke: 6, radius: 34, fontSize: "text-xl" },
        md: { size: 140, stroke: 10, radius: 60, fontSize: "text-3xl" },
        lg: { size: 200, stroke: 14, radius: 85, fontSize: "text-5xl" },
    };

    const { size: svgSize, stroke, radius, fontSize } = dimensions[size];
    const center = svgSize / 2;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = useTransform(count, [0, 100], [circumference, 0]);

    const colorClass = getScoreColor(score);

    return (
        <div className={cn("flex flex-col items-center justify-center", className)}>
            <div className="relative" style={{ width: svgSize, height: svgSize }}>
                <svg
                    width={svgSize}
                    height={svgSize}
                    viewBox={`0 0 ${svgSize} ${svgSize}`}
                    className="rotate-[-90deg]"
                >
                    <defs>
                        <linearGradient id="gradient-red" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#EF4444" />
                            <stop offset="100%" stopColor="#F87171" />
                        </linearGradient>
                        <linearGradient id="gradient-amber" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#F59E0B" />
                            <stop offset="100%" stopColor="#FBBF24" />
                        </linearGradient>
                        <linearGradient id="gradient-emerald" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#10B981" />
                            <stop offset="100%" stopColor="#34D399" />
                        </linearGradient>
                        <linearGradient id="gradient-indigo" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#6366F1" />
                            <stop offset="100%" stopColor="#8B5CF6" />
                        </linearGradient>
                    </defs>

                    {/* Background Track */}
                    <circle
                        cx={center}
                        cy={center}
                        r={radius}
                        fill="transparent"
                        stroke="currentColor"
                        strokeWidth={stroke}
                        className="text-muted/20"
                    />

                    {/* Progress Ring */}
                    <motion.circle
                        cx={center}
                        cy={center}
                        r={radius}
                        fill="transparent"
                        stroke={getScoreGradient(score)}
                        strokeWidth={stroke}
                        strokeDasharray={circumference}
                        style={{ strokeDashoffset }}
                        strokeLinecap="round"
                    />
                </svg>

                {/* Score Number in Center */}
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <motion.span
                        className={cn("font-bold tracking-tighter", fontSize, colorClass)}
                    >
                        {displayScore}
                    </motion.span>
                    <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                        Points
                    </span>
                </div>
            </div>

            {showLabel && (
                <motion.div
                    initial={animated ? { opacity: 0, y: 10 } : { opacity: 1, y: 0 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5, duration: 0.5 }}
                    className="mt-4 text-center"
                >
                    <p className="text-sm font-semibold text-foreground/80">{label}</p>
                    <p className={cn("text-xs font-medium", colorClass)}>
                        {score >= 90
                            ? "High EQ"
                            : score >= 80
                                ? "Medium EQ"
                                : "Low EQ"}
                    </p>
                </motion.div>
            )}
        </div>
    );
};

export default ScoreGauge;
