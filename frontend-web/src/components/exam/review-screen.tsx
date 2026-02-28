'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { Edit3, CheckCircle, Send, AlertCircle } from 'lucide-react';
import { useExamStore } from '@/stores/examStore';
import { cn } from '@/lib/utils';
import { AnimatePresence } from 'framer-motion';

interface ReviewScreenProps {
  onSubmit: () => void;
  isSubmitting?: boolean;
  error?: string | null;
}

export const ReviewScreen: React.FC<ReviewScreenProps> = ({
  onSubmit,
  isSubmitting = false,
  error = null,
}) => {
  const { questions, answers, jumpToQuestion, getAnsweredCount } = useExamStore();

  const answeredCount = getAnsweredCount();
  const totalQuestions = questions.length;
  const isComplete = answeredCount === totalQuestions;

  const handleEditQuestion = (index: number) => {
    jumpToQuestion(index);
  };

  const getAnswerLabel = (value: number) => {
    const labels = {
      1: 'Strongly Disagree',
      2: 'Disagree',
      3: 'Neutral',
      4: 'Agree',
      5: 'Strongly Agree',
    };
    return labels[value as keyof typeof labels] || `Value: ${value}`;
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Review Your Answers</h1>
          <p className="text-muted-foreground">
            Please review all your answers before submitting. You can edit any answer by clicking the "Edit" button.
          </p>
          <div className="mt-4 flex items-center justify-center gap-2">
            <CheckCircle className={cn(
              "h-5 w-5",
              isComplete ? "text-green-500" : "text-yellow-500"
            )} />
            <span className="text-sm font-medium">
              {answeredCount} of {totalQuestions} questions answered
            </span>
          </div>
        </div>

        {/* Progress Warning */}
        {!isComplete && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg"
          >
            <p className="text-yellow-700 dark:text-yellow-400 text-sm font-medium">
              ⚠️ You have unanswered questions. Please complete all questions before submitting.
            </p>
          </motion.div>
        )}

        {/* Questions Review */}
        <div className="space-y-4 mb-8">
          {questions.map((question, index) => {
            const answer = answers[question.id];
            const isAnswered = answer !== undefined;

            return (
              <motion.div
                key={question.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Card className={cn(
                  "transition-colors",
                  !isAnswered && "border-yellow-500/20 bg-yellow-500/5"
                )}>
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <CardTitle className="text-lg font-medium leading-relaxed">
                          {index + 1}. {question.text}
                        </CardTitle>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEditQuestion(index)}
                        className="flex items-center gap-2 shrink-0"
                      >
                        <Edit3 className="h-4 w-4" />
                        Edit
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "px-3 py-1 rounded-full text-sm font-medium",
                        isAnswered
                          ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                          : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                      )}>
                        {isAnswered ? getAnswerLabel(answer) : "Not answered"}
                      </div>
                      {isAnswered && (
                        <span className="text-sm text-muted-foreground">
                          (Value: {answer})
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>

        {/* Submit Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-muted/50 rounded-lg p-6 border"
        >
          <div className="text-center">
            <h3 className="text-lg font-semibold mb-2">Ready to Submit?</h3>
            <p className="text-muted-foreground mb-4">
              Once submitted, you cannot change your answers. Make sure everything looks correct.
            </p>

            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-6 p-4 bg-destructive/10 border border-destructive/20 rounded-md flex items-start gap-3 text-left"
                >
                  <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-destructive">
                      {isSubmitting ? "Retrying Submission..." : "Submission Failed"}
                    </p>
                    <p className="text-xs text-destructive/80 mt-1">{error}</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <Button
              onClick={onSubmit}
              disabled={isSubmitting || !isComplete}
              size="lg"
              className={cn(
                "px-8 py-3 text-white transition-colors",
                error
                  ? "bg-destructive hover:bg-destructive/90"
                  : "bg-green-600 hover:bg-green-700"
              )}
            >
              {isSubmitting ? (
                <>
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent mr-2" />
                  {error ? 'Retrying Submission...' : 'Submitting Exam...'}
                </>
              ) : (
                <>
                  <Send className="h-5 w-5 mr-2" />
                  {error ? 'Try Again' : 'Confirm & Submit Exam'}
                </>
              )}
            </Button>
            {!isComplete && (
              <p className="text-sm text-muted-foreground mt-3">
                Complete all questions to enable submission
              </p>
            )}
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};