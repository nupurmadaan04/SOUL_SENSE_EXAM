'use client';

import { useState, useEffect, useCallback } from 'react';
import { examsApi } from '@/lib/api/exams';
import { ExamResult } from '@/types/results';
import { ApiError } from '@/lib/api/errors';

interface UseResultsReturn {
  result: ExamResult | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useResults(id: number): UseResultsReturn {
  const [result, setResult] = useState<ExamResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchResult = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await examsApi.getExamResult(id);
      setResult(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load exam result');
      }
      console.error('Error fetching exam result:', err);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchResult();
  }, [fetchResult]);

  return {
    result,
    isLoading,
    error,
    refetch: fetchResult,
  };
}
