import { useState, useCallback } from 'react';
import { resultsApi } from '../lib/api/results';
import { DetailedExamResult, AssessmentResponse } from '../types/results';
import { ApiError } from '../lib/api/errors';

/** Sentinel value for "resource not found" vs. generic errors */
const NOT_FOUND_MESSAGE = 'No Result Found. The requested assessment does not exist or has been removed.';

interface UseResultsOptions {
  initialPage?: number;
  initialPageSize?: number;
  autoFetch?: boolean;
}

/**
 * Custom hook for managing assessment results and history.
 * Provides state for history list, detailed breakdowns, and loading/error status.
 */
export function useResults(options: UseResultsOptions = {}) {
  const [history, setHistory] = useState<AssessmentResponse[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(options.initialPage || 1);
  const [pageSize, setPageSize] = useState(options.initialPageSize || 10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [detailedResult, setDetailedResult] = useState<DetailedExamResult | null>(null);

  /**
   * Fetches paginated assessment history.
   */
  const fetchHistory = useCallback(
    async (page = currentPage, size = pageSize) => {
      setLoading(true);
      setError(null);
      try {
        const data = await resultsApi.getHistory(page, size);
        setHistory(data.assessments);
        setTotalCount(data.total);
        setCurrentPage(page);
        setPageSize(size);
        return data;
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : 'Failed to fetch assessment history';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [currentPage, pageSize]
  );

  /**
   * Fetches detailed results for a specific assessment.
   */
  const fetchDetailedResult = useCallback(async (assessmentId: number) => {
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const data = await resultsApi.getDetailedResult(assessmentId);
      if (!data) {
        // API returned successfully but with empty/null body
        setNotFound(true);
        setDetailedResult(null);
        return null;
      }
      setDetailedResult(data);
      return data;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        // Result was deleted or never existed — graceful "not found"
        setNotFound(true);
        setDetailedResult(null);
        setError(NOT_FOUND_MESSAGE);
        return null;
      }
      const message = err instanceof ApiError ? err.message : 'Failed to fetch detailed results';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Resets the detailed result state.
   */
  const clearDetailedResult = useCallback(() => {
    setDetailedResult(null);
    setNotFound(false);
  }, []);

  return {
    // State
    history,
    totalCount,
    currentPage,
    pageSize,
    loading,
    error,
    notFound,
    detailedResult,

    // Actions
    fetchHistory,
    fetchDetailedResult,
    clearDetailedResult,
    setCurrentPage,
    setPageSize,
  };
}
