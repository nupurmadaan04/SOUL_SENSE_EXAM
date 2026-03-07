import React, { Suspense } from 'react';
import { motion } from 'framer-motion';
import { JournalEntryCard } from './entry-card';
import { Skeleton } from '@/components/ui';

// Adapt JournalEntry for JournalEntryCard
function adaptEntry(entry: any) {
  return {
    id: entry.id,
    content: entry.content,
    mood_rating:
      entry.mood_score ||
      (entry.sentiment_score ? Math.round((entry.sentiment_score + 1) * 5) : undefined),
    tags: entry.tags || [],
    sentiment_score: entry.sentiment_score,
    created_at: entry.updated_at || entry.timestamp,
    updated_at: entry.updated_at || entry.timestamp,
  };
}

interface JournalListInnerProps {
  entries: any[];
  onEntryClick: (entry: any) => void;
}

function JournalListInner({ entries, onEntryClick }: JournalListInnerProps) {
  return (
    <div className="space-y-4">
      {entries.map((entry, index) => (
        <motion.div
          key={entry.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 }}
        >
          <JournalEntryCard
            entry={adaptEntry(entry)}
            onClick={onEntryClick}
            variant="expanded"
          />
        </motion.div>
      ))}
    </div>
  );
}

interface JournalListContainerProps {
  entries: any[];
  onEntryClick: (entry: any) => void;
  isLoading?: boolean;
}

export function JournalListContainer({ entries, onEntryClick, isLoading }: JournalListContainerProps) {
  if (isLoading && entries.length === 0) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="rounded-2xl border p-6 space-y-3 bg-background/60 backdrop-blur-xl shadow-xl shadow-black/5">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <div className="flex gap-2 pt-2">
              <Skeleton className="h-6 w-16 rounded-full" />
              <Skeleton className="h-6 w-20 rounded-full" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <Suspense
      fallback={
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="rounded-2xl border p-6 space-y-3 bg-background/60 backdrop-blur-xl shadow-xl shadow-black/5">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <div className="flex gap-2 pt-2">
                <Skeleton className="h-6 w-16 rounded-full" />
                <Skeleton className="h-6 w-20 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      }
    >
      <JournalListInner entries={entries} onEntryClick={onEntryClick} />
    </Suspense>
  );
}