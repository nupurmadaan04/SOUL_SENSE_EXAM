'use client';

import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Question } from '@/lib/api/questions';
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui';
import { cn } from '@/lib/utils';

interface QuestionCardProps {
  question: Question;
  selectedValue?: number;
  onSelect: (value: number) => void;
  disabled?: boolean;
  totalQuestions?: number;
  currentIndex?: number;
}

export const LIKERT_4_LABELS: Record<number, string> = {
  1: 'Strongly Disagree',
  2: 'Disagree',
  3: 'Agree',
  4: 'Strongly Agree',
};

export const QuestionCard: React.FC<QuestionCardProps> = ({
  question,
  selectedValue,
  onSelect,
  disabled = false,
  totalQuestions,
  currentIndex,
}) => {
  const optionsRef = useRef<(HTMLButtonElement | null)[]>([]);

  // Strict 4-point forced-choice scale (No Neutral)
  const options = [
    { value: 1, label: 'Strongly Disagree' },
    { value: 2, label: 'Disagree' },
    { value: 3, label: 'Agree' },
    { value: 4, label: 'Strongly Agree' },
  ];

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
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="w-full max-w-2xl mx-auto"
    >
      <Card className="overflow-hidden border border-border/80 shadow-2xl bg-card/90 backdrop-blur-md rounded-3xl">
        <CardHeader className="flex flex-row items-center justify-between pb-2 pt-6 px-6 sm:px-8">
          <div className="flex items-center space-x-2">
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-primary/10 text-primary border border-primary/20">
              {question.category || 'Emotional Insight'}
            </span>
          </div>
          {totalQuestions !== undefined && currentIndex !== undefined && (
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
              Question {currentIndex + 1} of {totalQuestions}
            </span>
          )}
        </CardHeader>

        <CardContent className="pt-6 pb-8 px-6 sm:px-8">
          <h2
            id={`question-${question.id}`}
            className="text-xl sm:text-2xl md:text-3xl font-black text-foreground leading-snug"
          >
            {question.text}
          </h2>
        </CardContent>

        <CardFooter className="flex flex-col space-y-4 pt-2 pb-8 px-6 sm:px-8">
          <div
            role="radiogroup"
            aria-labelledby={`question-${question.id}`}
            className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full"
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
                  onClick={() => onSelect(option.value)}
                  onKeyDown={(e) => handleKeyDown(e, idx)}
                  tabIndex={isSelected || (selectedValue === undefined && idx === 0) ? 0 : -1}
                  className={cn(
                    'relative flex flex-col items-center justify-center p-4 rounded-2xl transition-all duration-200 border-2 text-center group cursor-pointer',
                    'hover:scale-102 active:scale-98',
                    isSelected
                      ? 'bg-primary border-primary text-primary-foreground shadow-lg shadow-primary/30'
                      : 'bg-card border-border/80 text-foreground hover:border-primary/50 hover:bg-muted/30',
                    disabled && 'opacity-50 cursor-not-allowed hover:scale-100'
                  )}
                >
                  <span
                    className={cn(
                      'text-xl font-black mb-1',
                      isSelected ? 'text-primary-foreground' : 'text-foreground'
                    )}
                  >
                    {option.value}
                  </span>
                  <span
                    className={cn(
                      'text-[11px] uppercase tracking-wider font-black leading-tight text-center whitespace-normal',
                      isSelected ? 'text-primary-foreground' : 'text-muted-foreground'
                    )}
                  >
                    {option.label}
                  </span>

                  {isSelected && (
                    <motion.div
                      layoutId={`question-active-bg-${question.id}`}
                      className="absolute inset-0 rounded-2xl bg-primary -z-10"
                      transition={{ type: 'tween', ease: 'easeOut', duration: 0.3 }}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </CardFooter>
      </Card>
    </motion.div>
  );
};
