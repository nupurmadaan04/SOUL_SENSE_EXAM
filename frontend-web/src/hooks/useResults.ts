'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { resultsApi } from '@/lib/api/results';
import { ExamResult, ResultsHistory } from '@/types/results';
import { ApiError } from '@/lib/api/errors';

interface UseResultsOptions {
  historyPage?: number;
  historyPageSize?: number;
  resultId?: string | number;
  enabledHistory?: boolean;
  enabledResult?: boolean;
}

interface UseResultsReturn {
  result: ExamResult | null;
  results: ExamResult[];
  history: ResultsHistory | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useResults(options: UseResultsOptions = {}): UseResultsReturn {
  const {
    historyPage = 1,
    historyPageSize = 50,
    resultId,
    enabledHistory = true,
    enabledResult = true,
  } = options;

  const [result, setResult] = useState<ExamResult | null>(null);
  const [history, setHistory] = useState<ResultsHistory | null>(null);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [isResultLoading, setIsResultLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isMountedRef = useRef(true);

  const fetchHistory = useCallback(async () => {
    if (!enabledHistory) return;

    setIsHistoryLoading(true);
    setError(null);

    try {
      const data = await resultsApi.getHistory(historyPage, historyPageSize);
      if (!isMountedRef.current) return;
      setHistory(data);
    } catch (err) {
      if (!isMountedRef.current) return;
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to load results history.');
      }
    } finally {
      if (isMountedRef.current) {
        setIsHistoryLoading(false);
      }
    }
  }, [enabledHistory, historyPage, historyPageSize]);

  const fetchResult = useCallback(async () => {
    if (!enabledResult || resultId === undefined || resultId === null) return;

    setIsResultLoading(true);
    setError(null);

    try {
      const data = await resultsApi.getResult(resultId);
      if (!isMountedRef.current) return;
      setResult(data);
    } catch (err) {
      if (!isMountedRef.current) return;
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to load result details.');
      }
    } finally {
      if (isMountedRef.current) {
        setIsResultLoading(false);
      }
    }
  }, [enabledResult, resultId]);

  const refetch = useCallback(async () => {
    await Promise.all([fetchHistory(), fetchResult()]);
  }, [fetchHistory, fetchResult]);

  useEffect(() => {
    isMountedRef.current = true;
    fetchHistory();
    fetchResult();

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchHistory, fetchResult]);

  return {
    result,
    results: history?.results ?? [],
    history,
    isLoading: isHistoryLoading || isResultLoading,
    error,
    refetch,
  };
}
