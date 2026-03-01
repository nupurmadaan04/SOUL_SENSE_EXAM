import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { preferencesApi, UserPreferences } from '@/lib/api/preferences';
import { useCallback, useState, useRef, useEffect } from 'react';

export function usePreferences() {
    const queryClient = useQueryClient();
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
    const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

    const {
        data: preferences,
        isLoading,
        error,
        refetch,
    } = useQuery({
        queryKey: ['userPreferences'],
        queryFn: () => preferencesApi.getPreferences(),
    });

    const mutation = useMutation({
        mutationFn: (updates: Partial<UserPreferences>) => preferencesApi.updatePreferences(updates),
        onMutate: async (newPreferences) => {
            // Cancel any outgoing refetches (so they don't overwrite our optimistic update)
            await queryClient.cancelQueries({ queryKey: ['userPreferences'] });

            // Snapshot the previous value
            const previousPreferences = queryClient.getQueryData(['userPreferences']);

            // Optimistically update to the new value
            queryClient.setQueryData(['userPreferences'], (old: UserPreferences) => ({
                ...old,
                ...newPreferences,
            }));

            setSaveStatus('saving');

            // Return a context object with the snapshotted value
            return { previousPreferences };
        },
        onError: (err, newPreferences, context) => {
            // If the mutation fails, use the context returned from onMutate to roll back
            if (context?.previousPreferences) {
                queryClient.setQueryData(['userPreferences'], context.previousPreferences);
            }
            setSaveStatus('error');
            setTimeout(() => setSaveStatus('idle'), 3000);
        },
        onSuccess: () => {
            setSaveStatus('saved');
            setTimeout(() => setSaveStatus('idle'), 2000);
        },
        onSettled: () => {
            // Always refetch after error or success to ensure we have the correct data from the server
            queryClient.invalidateQueries({ queryKey: ['userPreferences'] });
        },
    });

    const updatePreferences = useCallback(
        (updates: Partial<UserPreferences>) => {
            mutation.mutate(updates);
        },
        [mutation]
    );

    const updatePreferencesDebounced = useCallback(
        (updates: Partial<UserPreferences>) => {
            // Optimistically update the UI immediately
            queryClient.setQueryData(['userPreferences'], (old: UserPreferences) => ({
                ...old,
                ...updates,
            }));

            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }

            setSaveStatus('saving');

            debounceTimerRef.current = setTimeout(() => {
                mutation.mutate(updates);
            }, 1000); // 1 second debounce
        },
        [mutation, queryClient]
    );

    useEffect(() => {
        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, []);

    return {
        preferences,
        isLoading,
        error,
        saveStatus,
        updatePreferences,
        updatePreferencesDebounced,
        refetch,
    };
}
