'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X,
    ChevronRight,
    ChevronLeft,
    Check,
    LayoutDashboard,
    Target,
    BookOpen,
    Settings,
    HelpCircle
} from 'lucide-react';
import { Button } from '@/components/ui';

interface Step {
    title: string;
    description: string;
    icon: React.ElementType;
    color: string;
}

const steps: Step[] = [
    {
        title: "Welcome to SoulSense",
        description: "Your journey to emotional intelligence and personal growth starts here. Let's take a quick tour of the key features.",
        icon: HelpCircle,
        color: "bg-blue-500",
    },
    {
        title: "Dashboard Overview",
        description: "Monitor your emotional trends, track your progress, and get AI-powered insights all in one place.",
        icon: LayoutDashboard,
        color: "bg-purple-500",
    },
    {
        title: "Goal Setting",
        description: "Set structured emotional growth goals and track your progress as you build resilience and self-awareness.",
        icon: Target,
        color: "bg-green-500",
    },
    {
        title: "Journaling",
        description: "Reflect on your daily experiences. Our AI analyzes your sentiment and emotional patterns to provide personalized advice.",
        icon: BookOpen,
        color: "bg-orange-500",
    },
    {
        title: "Personalization",
        description: "Customize your experience in settings, including themes, notification preferences, and AI tone.",
        icon: Settings,
        color: "bg-pink-500",
    }
];

interface OnboardingTutorialProps {
    onComplete: () => void;
    onSkip: () => void;
}

export const OnboardingTutorial: React.FC<OnboardingTutorialProps> = ({
    onComplete,
    onSkip
}) => {
    const [currentStep, setCurrentStep] = useState(0);
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        setIsVisible(true);
    }, []);

    const nextStep = () => {
        if (currentStep < steps.length - 1) {
            setCurrentStep(currentStep + 1);
        } else {
            onComplete();
        }
    };

    const prevStep = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
        }
    };

    const step = steps[currentStep];
    const Icon = step.icon;

    return (
        <AnimatePresence>
            {isVisible && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="bg-white dark:bg-gray-900 rounded-3xl shadow-2xl overflow-hidden max-w-lg w-full relative"
                    >
                        {/* Header / Banner */}
                        <div className={`h-32 ${step.color} flex items-center justify-center transition-colors duration-500`}>
                            <motion.div
                                key={currentStep}
                                initial={{ scale: 0, rotate: -45 }}
                                animate={{ scale: 1, rotate: 0 }}
                                transition={{ type: "spring", damping: 12 }}
                                className="bg-white/20 p-4 rounded-2xl backdrop-blur-md"
                            >
                                <Icon className="w-12 h-12 text-white" />
                            </motion.div>
                        </div>

                        {/* Close/Skip button */}
                        <button
                            onClick={onSkip}
                            className="absolute top-4 right-4 p-2 rounded-full bg-black/10 hover:bg-black/20 dark:bg-white/10 dark:hover:bg-white/20 transition-colors"
                        >
                            <X className="w-5 h-5 text-white" />
                        </button>

                        {/* Content */}
                        <div className="p-8 text-center">
                            <motion.div
                                key={currentStep}
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                transition={{ duration: 0.3 }}
                            >
                                <h2 className="text-2xl font-bold mb-3 text-gray-900 dark:text-white">
                                    {step.title}
                                </h2>
                                <p className="text-gray-600 dark:text-gray-400 leading-relaxed mb-8">
                                    {step.description}
                                </p>
                            </motion.div>

                            {/* Progress dots */}
                            <div className="flex justify-center gap-2 mb-8">
                                {steps.map((_, index) => (
                                    <div
                                        key={index}
                                        className={`h-2 rounded-full transition-all duration-300 ${index === currentStep
                                                ? `w-8 ${step.color}`
                                                : "w-2 bg-gray-200 dark:bg-gray-700"
                                            }`}
                                    />
                                ))}
                            </div>

                            {/* Actions */}
                            <div className="flex items-center justify-between">
                                <Button
                                    variant="ghost"
                                    onClick={onSkip}
                                    className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                                >
                                    Skip tutorial
                                </Button>

                                <div className="flex gap-3">
                                    {currentStep > 0 && (
                                        <Button
                                            variant="outline"
                                            onClick={prevStep}
                                            className="rounded-xl flex items-center gap-1"
                                        >
                                            <ChevronLeft className="w-4 h-4" /> Back
                                        </Button>
                                    )}

                                    <Button
                                        onClick={nextStep}
                                        className={`${step.color} hover:opacity-90 transition-opacity text-white rounded-xl shadow-lg shadow-${step.color.split('-')[1]}-500/20 px-8 flex items-center gap-1`}
                                    >
                                        {currentStep === steps.length - 1 ? (
                                            <>Finish <Check className="w-4 h-4" /></>
                                        ) : (
                                            <>Next <ChevronRight className="w-4 h-4" /></>
                                        )}
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
};
