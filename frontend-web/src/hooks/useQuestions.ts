'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { questionsApi, Question, QuestionsResponse } from '@/lib/api/questions';
import { ApiError } from '@/lib/api/errors';

interface UseQuestionsOptions {
  category?: string;
  count?: number;
  enabled?: boolean;
}

interface UseQuestionsReturn {
  questions: Question[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// Simple in-memory cache
const questionsCache = new Map<string, { data: Question[]; timestamp: number }>();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

function getCacheKey(category?: string, count?: number): string {
  return `${category || 'all'}-${count || 'all'}`;
}

export function useQuestions(options: UseQuestionsOptions = {}): UseQuestionsReturn {
  const { category, count, enabled = true } = options;
  const [questions, setQuestions] = useState<Question[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use ref to track if component is mounted
  const isMountedRef = useRef(true);

  const cacheKey = getCacheKey(category, count);

  const fetchQuestions = useCallback(async () => {
    if (!enabled) return;

    // Check cache first
    const cached = questionsCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      setQuestions(cached.data);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response: QuestionsResponse = await questionsApi.getQuestions({
        category,
        count,
      });

      if (!isMountedRef.current) return;

      // Update cache
      questionsCache.set(cacheKey, {
        data: response.questions,
        timestamp: Date.now(),
      });

      setQuestions(response.questions);
    } catch (err) {
      if (!isMountedRef.current) return;

      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred while fetching questions');
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [category, count, enabled, cacheKey]);

  const refetch = useCallback(async () => {
    // Clear cache for this key
    questionsCache.delete(cacheKey);
    await fetchQuestions();
  }, [fetchQuestions, cacheKey]);

  useEffect(() => {
    isMountedRef.current = true;
    fetchQuestions();

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchQuestions]);

  return {
    questions,
    isLoading,
    error,
    refetch,
  };
}