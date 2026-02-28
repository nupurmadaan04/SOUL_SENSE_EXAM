'use client';

import React, { useState, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { examsApi, ExamSubmissionRequest, ExamSubmissionResponse } from '@/lib/api/exams';
import { ApiError } from '@/lib/api/errors';

interface UseExamSubmitReturn {
  submitExam: (data: ExamSubmissionRequest) => Promise<ExamSubmissionResponse | null>;
  isSubmitting: boolean;
  error: string | null;
  result: ExamSubmissionResponse | null;
  reset: () => void;
}

export function useExamSubmit(): UseExamSubmitReturn {
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExamSubmissionResponse | null>(null);

  // Use ref to track if component is mounted
  const isMountedRef = useRef(false);

  const submitExam = useCallback(
    async (data: ExamSubmissionRequest): Promise<ExamSubmissionResponse | null> => {
      if (!isMountedRef.current) return null;

      setIsSubmitting(true);
      setResult(null);
      // We don't clear error here to allow "Retrying..." UI states

      try {
        const examResult = await examsApi.submitExam(data);

        if (!isMountedRef.current) return null;

        setError(null); // Clear error on success
        setResult(examResult);

        // Invalidate dashboard queries to refresh data
        queryClient.invalidateQueries({ queryKey: ['dashboard'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });

        return examResult;
      } catch (err) {
        if (!isMountedRef.current) return null;

        if (err instanceof ApiError) {
          // Handle validation errors
          if (err.status === 422 && err.data?.detail) {
            // Handle field validation errors
            if (Array.isArray(err.data.detail)) {
              const fieldErrors = err.data.detail
                .map((error: any) => {
                  const fieldName = error.loc && error.loc.length > 1
                    ? error.loc[error.loc.length - 1].toString()
                    : 'unknown_field';
                  return `Error in ${fieldName}: ${error.msg}`;
                })
                .join(', ');
              setError(`Validation failed: ${fieldErrors}`);
            } else {
              setError(err.message);
            }
          } else if (err.status >= 400 && err.status < 500) {
            // Client errors (400-499)
            setError(err.message);
          } else if (err.status >= 500) {
            // Server errors
            setError('Server error occurred. Please try again later.');
          } else if (err.isNetworkError) {
            // Network errors
            setError(
              'Network connection failed. Please check your internet connection and try again.'
            );
          } else {
            setError(err.message);
          }
        } else {
          // Unexpected errors
          setError('An unexpected error occurred. Please try again.');
        }

        return null;
      } finally {
        if (isMountedRef.current) {
          setIsSubmitting(false);
        }
      }
    },
    []
  );

  const reset = useCallback(() => {
    setIsSubmitting(false);
    setError(null);
    setResult(null);
  }, []);

  // Cleanup on unmount
  React.useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  return {
    submitExam,
    isSubmitting,
    error,
    result,
    reset,
  };
}
