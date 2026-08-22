'use client';

import React, { useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Question } from '@/lib/api/questions';
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui';
import { cn } from '@/lib/utils';
import { useSwipe, useHapticFeedback, useBreakpoint } from '@/hooks/useMobileGestures';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface MobileQuestionCardProps {
  question: Question;
  selectedValue?: number;
  onSelect: (value: number) => void;
  onPrevious?: () => void;
  onNext?: () => void;
  disabled?: boolean;
  totalQuestions?: number;
  currentIndex?: number;
  canGoBack?: boolean;
}

const LIKERT_LABELS: Record<number, string> = {
  1: 'Strongly Disagree',
  2: 'Disagree',
  3: 'Agree',
  4: 'Strongly Agree',
};

const LIKERT_SHORT_LABELS: Record<number, string> = {
  1: 'SD',
  2: 'D',
  3: 'A',
  4: 'SA',
};

export const MobileQuestionCard: React.FC<MobileQuestionCardProps> = ({
  question,
  selectedValue,
  onSelect,
  onPrevious,
  onNext,
  disabled = false,
  totalQuestions,
  currentIndex,
  canGoBack = true,
}) => {
  const optionsRef = useRef<(HTMLButtonElement | null)[]>([]);
  const [direction, setDirection] = useState(0);
  const { isMobile } = useBreakpoint();
  const { light, medium } = useHapticFeedback();

  const options = [
    { value: 1, label: 'Strongly Disagree' },
    { value: 2, label: 'Disagree' },
    { value: 3, label: 'Agree' },
    { value: 4, label: 'Strongly Agree' },
  ];

  const handleSwipeLeft = useCallback(() => {
    if (!disabled && selectedValue !== undefined && onNext) {
      setDirection(1);
      medium();
      onNext();
    }
  }, [disabled, selectedValue, onNext, medium]);

  const handleSwipeRight = useCallback(() => {
    if (!disabled && canGoBack && onPrevious) {
      setDirection(-1);
      medium();
      onPrevious();
    }
  }, [disabled, canGoBack, onPrevious, medium]);

  const swipeRef = useSwipe({
    onSwipeLeft: handleSwipeLeft,
    onSwipeRight: handleSwipeRight,
    threshold: 75,
  });

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    if (disabled) return;

    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      const nextIndex = (index + 1) % options.length;
      optionsRef.current[nextIndex]?.focus();
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      const prevIndex = (index - 1 + options.length) % options.length;
      optionsRef.current[prevIndex]?.focus();
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(options[index].value);
      light();
    }
  };

  const handleSelect = (value: number) => {
    onSelect(value);
    light();
  };

  const variants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 300 : -300,
      opacity: 0,
    }),
    center: {
      x: 0,
      opacity: 1,
    },
    exit: (direction: number) => ({
      x: direction < 0 ? 300 : -300,
      opacity: 0,
    }),
  };

  return (
    <div ref={swipeRef as React.RefObject<HTMLDivElement>} className="w-full touch-pan-y">
      <AnimatePresence mode="wait" custom={direction}>
        <motion.div
          key={question.id}
          custom={direction}
          variants={variants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="w-full max-w-2xl mx-auto"
        >
          <Card className="overflow-hidden border-none shadow-xl bg-white/80 dark:bg-slate-900/80 backdrop-blur-md">
            <CardHeader className="flex flex-row items-center justify-between pb-2 px-4 md:px-6">
              <div className="flex items-center space-x-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
                  {question.category || 'General'}
                </span>
              </div>
              {totalQuestions !== undefined && currentIndex !== undefined && (
                <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
                  {currentIndex + 1} / {totalQuestions}
                </span>
              )}
            </CardHeader>

            <CardContent className="pt-4 pb-6 px-4 md:pt-6 md:pb-8 md:px-6">
              <h2
                id={`question-${question.id}`}
                className="text-xl md:text-2xl lg:text-3xl font-bold text-slate-800 dark:text-slate-100 leading-tight"
              >
                {question.text}
              </h2>
            </CardContent>

            <CardFooter className="flex flex-col space-y-4 pt-2 pb-6 px-4 md:pt-4 md:pb-8 md:px-6">
              <div
                role="radiogroup"
                aria-labelledby={`question-${question.id}`}
                className={cn(
                  'grid gap-3 w-full',
                  isMobile ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-5'
                )}
              >
                {options.map((option, idx) => {
                  const isSelected = selectedValue === option.value;

                  return (
                    <button
                      key={option.value}
                      ref={(el: HTMLButtonElement | null) => {
                        optionsRef.current[idx] = el;
                      }}
                      role="radio"
                      aria-checked={isSelected}
                      disabled={disabled}
                      onClick={() => handleSelect(option.value)}
                      onKeyDown={(e) => handleKeyDown(e, idx)}
                      tabIndex={isSelected || (selectedValue === undefined && idx === 0) ? 0 : -1}
                      className={cn(
                        'relative flex items-center justify-center p-4 rounded-xl transition-all duration-200 border-2 text-center group touch-manipulation',
                        'min-h-touch w-full',
                        'hover:scale-[1.02] active:scale-[0.98]',
                        isSelected
                          ? 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30'
                          : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-indigo-400 dark:hover:border-indigo-500',
                        disabled && 'opacity-50 cursor-not-allowed hover:scale-100'
                      )}
                    >
                      <div className="flex items-center gap-3 w-full">
                        <span
                          className={cn(
                            'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold',
                            isSelected
                              ? 'bg-white/20 text-white'
                              : 'bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white'
                          )}
                        >
                          {option.value}
                        </span>
                        <span className={cn(
                          'text-sm font-medium text-left flex-1',
                          isMobile ? '' : 'hidden sm:block'
                        )}>
                          {isMobile ? LIKERT_SHORT_LABELS[option.value] : option.label}
                        </span>
                      </div>

                      {isSelected && (
                        <motion.div
                          layoutId={`mobile-question-active-bg-${question.id}`}
                          className="absolute inset-0 rounded-xl bg-indigo-600 -z-10"
                          transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                        />
                      )}
                    </button>
                  );
                })}
              </div>

              {isMobile && (onPrevious || onNext) && (
                <div className="flex items-center justify-between w-full pt-4">
                  <button
                    onClick={() => {
                      if (canGoBack && onPrevious) {
                        setDirection(-1);
                        onPrevious();
                      }
                    }}
                    disabled={!canGoBack || disabled}
                    className={cn(
                      'flex items-center gap-2 px-4 py-3 rounded-xl transition-colors touch-manipulation min-h-touch',
                      canGoBack && !disabled
                        ? 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                        : 'bg-slate-50 dark:bg-slate-900 text-slate-300 dark:text-slate-600 cursor-not-allowed'
                    )}
                  >
                    <ChevronLeft className="h-5 w-5" />
                    <span className="text-sm font-medium">Previous</span>
                  </button>

                  <button
                    onClick={() => {
                      if (selectedValue !== undefined && onNext) {
                        setDirection(1);
                        onNext();
                      }
                    }}
                    disabled={selectedValue === undefined || disabled}
                    className={cn(
                      'flex items-center gap-2 px-4 py-3 rounded-xl transition-colors touch-manipulation min-h-touch',
                      selectedValue !== undefined && !disabled
                        ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed'
                    )}
                  >
                    <span className="text-sm font-medium">Next</span>
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              )}
            </CardFooter>
          </Card>
        </motion.div>
      </AnimatePresence>

      <div className="text-center mt-4 text-xs text-slate-400 dark:text-slate-500 md:hidden">
        Swipe to navigate
      </div>
    </div>
  );
};
