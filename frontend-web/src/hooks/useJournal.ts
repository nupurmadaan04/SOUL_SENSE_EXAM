import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback } from 'react';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface JournalEntry {
  id: number;
  content: string;
  mood_rating: number;
  energy_level: number;
  stress_level: number;
  tags: string[];
  sentiment_score: number;
  created_at: string;
  updated_at: string;
  timestamp: string; // Add timestamp as it's used for keyset pagination
}

export interface JournalQueryParams {
  limit?: number;
  cursor?: string;
  startDate?: string;
  endDate?: string;
  moodMin?: number;
  moodMax?: number;
  tags?: string[];
  search?: string;
}

interface JournalCursorResponse {
  data: JournalEntry[];
  next_cursor: string | null;
  has_more: boolean;
}

const API_BASE = '/journal'; // apiClient prepends the rest

export function useJournal(filters: JournalQueryParams = {}) {
  const queryClient = useQueryClient();
const API_BASE = '/journal';

export function useJournal(initialParams: JournalQueryParams = {}, suspense = false) {
  const queryClient = useQueryClient();
  const [entry, setEntry] = useState<JournalEntry | null>(null);
  const [params, setParams] = useState<JournalQueryParams>(initialParams);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [entries, setEntries] = useState<JournalEntry[]>([]);

  // Helper to build query string
  const buildQueryString = (params: Record<string, any>) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) {
          if (value.length > 0) query.append(key, value.join(','));
        } else {
          query.append(key, String(value));
        }
      }
    });
    return query.toString();
  };

  // Infinite Scroll Query
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
    refetch,
  } = useInfiniteQuery({
    queryKey: ['journals', filters],
    queryFn: async ({ pageParam = null }) => {
      const params: any = {
        limit: filters.limit || 25,
        cursor: pageParam as string | null,
      };

      if (filters.startDate) params.start_date = filters.startDate;
      if (filters.endDate) params.end_date = filters.endDate;
      if (filters.search) params.search = filters.search;
      if (filters.tags && filters.tags.length > 0) params.tags = filters.tags;
  const {
    data: journalData,
    isLoading: isQueryLoading,
    refetch,
  } = useQuery({
    queryKey: ['journal', 'entries', params],
    queryFn: async () => {
      const queryString = buildQueryString(params);
      return await apiClient<JournalResponse>(`${API_BASE}?${queryString}`);
    },
  });

  const queryEntries = journalData?.entries || [];
  const queryTotal = journalData?.total || 0;

      const queryString = buildQueryString(params);
      return apiClient<JournalCursorResponse>(`${API_BASE}/?${queryString}`);
    },
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    initialPageParam: null as string | null,
    staleTime: 30000, // 30 seconds
  });

  // Flatten entries from all pages
  const entries = data?.pages.flatMap((page) => page.data) ?? [];

  // Mutations
  const createMutation = useMutation({
    mutationFn: async (newEntry: any) => {
      return apiClient.post(API_BASE + '/', newEntry);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journals'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, updates }: { id: number; updates: any }) => {
      return apiClient.put(`${API_BASE}/${id}`, updates);
    },
    onSuccess: (updatedData: any) => {
      queryClient.invalidateQueries({ queryKey: ['journals'] });
      queryClient.setQueryData(['journal', updatedData.id], updatedData);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      return apiClient.delete(`${API_BASE}/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journals'] });
    },
  });

  // Single Entry Fetch (standard query)
  const fetchEntry = async (id: number) => {
    return queryClient.fetchQuery({
      queryKey: ['journal', id],
      queryFn: async () => {
        return apiClient(`${API_BASE}/${id}`);
      }
    });
  };

  return {
    entries,
    isLoading,
    isError,
    error: error instanceof Error ? error.message : 'Unknown error',
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
    refetch,
    loadMore: fetchNextPage,
    createEntry: createMutation.mutateAsync,
    updateEntry: (id: number, updates: any) =>
      updateMutation.mutateAsync({ id, updates }),
    deleteEntry: deleteMutation.mutateAsync,
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiClient<JournalEntry>(`${API_BASE}/${id}`);
      setEntry(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  //create entry
  const createEntry = async (newEntry: Partial<JournalEntry>) => {
    const tempId = Date.now();

    const optimisticEntry: JournalEntry = {
      id: tempId,
      content: newEntry.content || '',
      mood_rating: newEntry.mood_rating || 0,
      energy_level: newEntry.energy_level || 0,
      stress_level: newEntry.stress_level || 0,
      tags: newEntry.tags || [],
      sentiment_score: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    setEntries((prev: JournalEntry[]) => [optimisticEntry, ...prev]);

    try {
      const saved = await apiClient<JournalEntry>(API_BASE, {
        method: 'POST',
        body: JSON.stringify(newEntry),
      });

      setEntries((prev: JournalEntry[]) =>
        prev.map((e: JournalEntry) => (e.id === tempId ? saved : e))
      );
      // Let React Query know the data is stale
      queryClient.invalidateQueries({ queryKey: ['journal', 'entries'] });
      return saved;
    } catch (err: any) {
      setEntries((prev: JournalEntry[]) => prev.filter((e) => e.id !== tempId));
      setError(err.message);
      throw err;
    }
  };

  //update entry
  const updateEntry = async (id: number, updates: Partial<JournalEntry>) => {
    const previous = entries;

    setEntries((prev: JournalEntry[]) =>
      prev.map((e: JournalEntry) => (e.id === id ? { ...e, ...updates } : e))
    );

    try {
      const updated = await apiClient<JournalEntry>(`${API_BASE}/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      });

      setEntries((prev: JournalEntry[]) =>
        prev.map((e: JournalEntry) => (e.id === id ? updated : e))
      );
      // Let React Query know the data is stale
      queryClient.invalidateQueries({ queryKey: ['journal', 'entries'] });
      return updated;
    } catch (err: any) {
      setEntries(previous);
      setError(err.message);
      throw err;
    }
  };

  //delete entry
  const deleteEntry = async (id: number) => {
    const previous = entries;

    setEntries((prev: JournalEntry[]) => prev.filter((e) => e.id !== id));
    try {
      await apiClient(`${API_BASE}/${id}`, {
        method: 'DELETE',
      });
      // Let React Query know the data is stale
      queryClient.invalidateQueries({ queryKey: ['journal', 'entries'] });
    } catch (err: any) {
      setEntries(previous);
      setError(err.message);
      throw err;
    }
  };
  return {
    entries: queryEntries,
    entry,
    total: queryTotal,
    page: params.page || 1,
    per_page: params.per_page || 10,
    totalPages: Math.ceil(queryTotal / (params.per_page || 10)),
    hasNextPage: (params.page || 1) * (params.per_page || 10) < queryTotal,
    hasPrevPage: (params.page || 1) > 1,
    isLoading,
    error,
    setParams,
    setPage: (p: number) => setParams((prev) => ({ ...prev, page: p })),
    setFilters: (f: Partial<JournalQueryParams>) =>
      setParams((prev) => ({ ...prev, ...f, page: 1 })),
    refetch,
    loadMore: () => setParams((prev) => ({ ...prev, page: (prev.page || 1) + 1 })),
    fetchEntry,
    total: entries.length,
  };
}
