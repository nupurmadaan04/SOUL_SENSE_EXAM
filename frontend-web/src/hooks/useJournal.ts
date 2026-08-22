import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface JournalEntry {
  id: number;
  content: string;
  mood_rating?: number;
  energy_level?: number;
  stress_level?: number;
  sleep_hours?: number;
  sleep_quality?: number;
  work_hours?: number;
  screen_time_mins?: number;
  tags?: string[];
  sentiment_score?: number;
  created_at: string;
  updated_at?: string;
  timestamp?: string;
  entry_date?: string;
  title?: string;
  daily_schedule?: string;
  privacy_level?: string;
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
  entries?: JournalEntry[];
  data?: JournalEntry[];
  next_cursor?: string | null;
  has_more?: boolean;
  total?: number;
}

const API_BASE = '/journal';

export function useJournal(filters: JournalQueryParams = {}) {
  const queryClient = useQueryClient();

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

  // Keyset / Cursor or Offset Paginated Query
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
      };
      if (pageParam) params.cursor = pageParam;
      if (filters.startDate) params.start_date = filters.startDate;
      if (filters.endDate) params.end_date = filters.endDate;
      if (filters.search) params.search = filters.search;
      if (filters.tags && filters.tags.length > 0) params.tags = filters.tags;

      const queryString = buildQueryString(params);
      const res = await apiClient<any>(`${API_BASE}?${queryString}`);
      const items = res?.entries || res?.data || (Array.isArray(res) ? res : []);
      return {
        data: items,
        next_cursor: res?.next_cursor || null,
        has_more: res?.has_more ?? false,
      };
    },
    getNextPageParam: (lastPage) => lastPage?.next_cursor ?? undefined,
    initialPageParam: null as string | null,
    staleTime: 30000,
  });

  const entries = data?.pages.flatMap((page) => page.data) ?? [];

  const createMutation = useMutation({
    mutationFn: async (newEntry: any) => {
      return apiClient(API_BASE, {
        method: 'POST',
        body: JSON.stringify(newEntry),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journals'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, updates }: { id: number; updates: any }) => {
      return apiClient(`${API_BASE}/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      });
    },
    onSuccess: (updatedData: any) => {
      queryClient.invalidateQueries({ queryKey: ['journals'] });
      if (updatedData?.id) {
        queryClient.setQueryData(['journal', updatedData.id], updatedData);
      }
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      return apiClient(`${API_BASE}/${id}`, {
        method: 'DELETE',
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journals'] });
    },
  });

  const fetchEntry = async (id: number) => {
    return queryClient.fetchQuery({
      queryKey: ['journal', id],
      queryFn: async () => {
        return apiClient(`${API_BASE}/${id}`);
      },
    });
  };

  return {
    entries,
    isLoading,
    isError,
    error: error instanceof Error ? error.message : null,
    hasNextPage: !!hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
    refetch,
    loadMore: fetchNextPage,
    createEntry: createMutation.mutateAsync,
    updateEntry: (id: number, updates: any) =>
      updateMutation.mutateAsync({ id, updates }),
    deleteEntry: deleteMutation.mutateAsync,
    fetchEntry,
    total: entries.length,
  };
}
