'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useJournal } from '@/hooks/useJournal';
import { journalApi, CreateJournalEntry, JournalFilters } from '@/lib/api/journal';
import { ErrorDisplay, Skeleton } from '@/components/common';
import { Button, Card, CardContent, Input, Slider } from '@/components/ui';
import { JournalEntryCard } from '@/components/journal';
import { JournalListContainer } from '@/components/journal';
// Dynamically import MoodTrend to avoid loading recharts on initial bundle
import { MoodTrend } from '@/lib/dynamic-imports';
import {
  BookOpen,
  Plus,
  Calendar,
  Tag,
  Search,
  X,
  ChevronDown,
  ChevronUp,
  Filter,
  Sparkles,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import InfiniteScroll from 'react-infinite-scroll-component';

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
    created_at: entry.timestamp,
    updated_at: entry.timestamp,
  };
}

export default function JournalPage() {
  const router = useRouter();
  const [isNewEntryOpen, setIsNewEntryOpen] = useState(false);
  const [isChartCollapsed, setIsChartCollapsed] = useState(false);
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const [newEntry, setNewEntry] = useState<CreateJournalEntry>({
    content: '',
    title: '',
    tags: [],
  });
  const [tagInput, setTagInput] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Filters state
  const [filters, setFilters] = useState<JournalFilters>({});
  const [tempFilters, setTempFilters] = useState<JournalFilters>({});

  const {
    entries,
    total,
    isLoading: loading,
    error,
    hasNextPage,
    refetch,
    loadMore,
  } = useJournal(filters, true);

  const setJournalFilters = (newFilters: JournalFilters) => {
    setFilters(newFilters);
  };

  const handleSubmit = useCallback(async () => {
    if (!newEntry.content.trim()) return;
    setSubmitting(true);
    try {
      await journalApi.createEntry(newEntry);
      setNewEntry({ content: '', title: '', tags: [] });
      setIsNewEntryOpen(false);
      refetch();
    } catch {
      // Error handling could be improved with a toast system
    } finally {
      setSubmitting(false);
    }
  }, [newEntry, refetch]);

  const handleAddTag = () => {
    const tag = tagInput.trim().toLowerCase();
    if (tag && !newEntry.tags?.includes(tag)) {
      setNewEntry((prev) => ({ ...prev, tags: [...(prev.tags || []), tag] }));
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setNewEntry((prev) => ({ ...prev, tags: prev.tags?.filter((t) => t !== tag) }));
  };

  const handleEntryClick = (entry: any) => {
    router.push(`/journal/${entry.id}`);
  };

  const handleApplyFilters = () => {
    setJournalFilters(tempFilters);
    setIsFiltersOpen(false);
  };

  const handleClearFilters = () => {
    setTempFilters({});
    setJournalFilters({});
    setIsFiltersOpen(false);
  };

  const handleLoadMore = () => {
    loadMore();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-8 max-w-6xl mx-auto"
    >
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-black tracking-tight flex items-center gap-3">
            <BookOpen className="w-7 h-7 text-primary" />
            Journal
          </h1>
          <p className="text-muted-foreground mt-2">
            Reflect on your emotional journey. {total > 0 && `${total} entries`}
          </p>
        </div>
        <Button
          onClick={() => setIsNewEntryOpen(!isNewEntryOpen)}
          className="rounded-full px-6 shadow-lg shadow-primary/20 hover:scale-105 transition-transform"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Entry
        </Button>
      </div>

      {/* New Entry Form */}
      <AnimatePresence>
        {isNewEntryOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="rounded-[2rem] border-none bg-background/60 backdrop-blur-xl shadow-xl shadow-black/5 overflow-hidden">
              <CardContent className="p-8 space-y-5">
                <div className="flex items-center gap-2 text-primary">
                  <Sparkles className="w-5 h-5" />
                  <span className="text-sm font-bold uppercase tracking-wider">
                    New Journal Entry
                  </span>
                </div>
                <Input
                  type="text"
                  placeholder="Title (optional)"
                  value={newEntry.title}
                  onChange={(e) => setNewEntry((prev) => ({ ...prev, title: e.target.value }))}
                  className="rounded-xl"
                />
                <textarea
                  placeholder="What's on your mind today?"
                  value={newEntry.content}
                  onChange={(e) => setNewEntry((prev) => ({ ...prev, content: e.target.value }))}
                  rows={6}
                  className="w-full px-4 py-3 rounded-xl border bg-muted/30 text-sm leading-relaxed resize-none focus:ring-2 focus:ring-primary/40 outline-none transition-all placeholder:text-muted-foreground/60"
                />

                {/* Tags */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Tag className="w-4 h-4 text-muted-foreground" />
                    <Input
                      type="text"
                      placeholder="Add a tag and press Enter"
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                      className="flex-1 rounded-lg"
                    />
                  </div>
                  {(newEntry.tags?.length ?? 0) > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {newEntry.tags?.map((tag) => (
                        <span
                          key={tag}
                          className="flex items-center gap-1 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium"
                        >
                          #{tag}
                          <button
                            onClick={() => handleRemoveTag(tag)}
                            className="hover:text-red-500 transition-colors"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-3">
                  <Button
                    variant="outline"
                    onClick={() => setIsNewEntryOpen(false)}
                    className="rounded-full"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSubmit}
                    disabled={submitting || !newEntry.content.trim()}
                    className="rounded-full px-6 shadow-lg shadow-primary/20"
                  >
                    {submitting ? (
                      <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin mr-2" />
                    ) : null}
                    {submitting ? 'Saving...' : 'Save Entry'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mood Trend Chart */}
      <Card className="rounded-[2rem] border-none bg-background/60 backdrop-blur-xl shadow-xl shadow-black/5 overflow-hidden">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">Mood Trends</h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsChartCollapsed(!isChartCollapsed)}
              className="rounded-full"
            >
              {isChartCollapsed ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronUp className="w-4 h-4" />
              )}
            </Button>
          </div>
          <AnimatePresence>
            {!isChartCollapsed && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <MoodTrend entries={entries.map(adaptEntry)} timeRange="30d" showAverage={true} />
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>

      {/* Search and Filter Bar */}
      <Card className="rounded-[2rem] border-none bg-background/60 backdrop-blur-xl shadow-lg shadow-black/5">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Filter className="w-5 h-5" />
              Search & Filters
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsFiltersOpen(!isFiltersOpen)}
              className="rounded-full"
            >
              {isFiltersOpen ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </Button>
          </div>

          {/* Quick Search */}
          <div className="flex gap-4 mb-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search entries..."
                value={tempFilters.search || ''}
                onChange={(e) => setTempFilters((prev) => ({ ...prev, search: e.target.value }))}
                className="pl-10 rounded-xl"
                onKeyDown={(e) => e.key === 'Enter' && handleApplyFilters()}
              />
            </div>
            <Button onClick={handleApplyFilters} className="rounded-full px-6">
              Apply Filters
            </Button>
            <Button variant="outline" onClick={handleClearFilters} className="rounded-full">
              Clear
            </Button>
          </div>

          {/* Advanced Filters */}
          <AnimatePresence>
            {isFiltersOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="space-y-4 pt-4 border-t"
              >
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Date Range */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Start Date</label>
                    <Input
                      type="date"
                      value={tempFilters.startDate || ''}
                      onChange={(e) =>
                        setTempFilters((prev) => ({ ...prev, startDate: e.target.value }))
                      }
                      className="rounded-lg"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">End Date</label>
                    <Input
                      type="date"
                      value={tempFilters.endDate || ''}
                      onChange={(e) =>
                        setTempFilters((prev) => ({ ...prev, endDate: e.target.value }))
                      }
                      className="rounded-lg"
                    />
                  </div>

                  {/* Mood Range */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      Min Mood ({tempFilters.moodMin || 0})
                    </label>
                    <Slider
                      value={tempFilters.moodMin || 0}
                      onChange={(value) => setTempFilters((prev) => ({ ...prev, moodMin: value }))}
                      max={100}
                      step={1}
                      className="w-full"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      Max Mood ({tempFilters.moodMax || 100})
                    </label>
                    <Slider
                      value={tempFilters.moodMax || 100}
                      onChange={(value) => setTempFilters((prev) => ({ ...prev, moodMax: value }))}
                      max={100}
                      step={1}
                      className="w-full"
                    />
                  </div>
                </div>

                {/* Tags */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Tags (comma separated)</label>
                  <Input
                    placeholder="work, family, health"
                    value={tempFilters.tags?.join(', ') || ''}
                    onChange={(e) =>
                      setTempFilters((prev) => ({
                        ...prev,
                        tags: e.target.value
                          ? e.target.value.split(',').map((t) => t.trim())
                          : undefined,
                      }))
                    }
                    className="rounded-lg"
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>

      {/* Error State */}
      {error && <ErrorDisplay message={error} onRetry={refetch} />}

      {/* Empty State */}
      {!loading && !error && entries.length === 0 && (
        <Card className="rounded-[2rem] border-dashed border-2 bg-muted/10">
          <CardContent className="p-12 text-center space-y-4">
            <div className="mx-auto w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
              <BookOpen className="w-8 h-8 text-primary" />
            </div>
            <h3 className="text-lg font-bold">No journal entries yet</h3>
            <p className="text-muted-foreground text-sm max-w-xs mx-auto">
              Start your reflection journey. Tap &quot;New Entry&quot; to write your first journal
              entry.
            </p>
            <Button onClick={() => setIsNewEntryOpen(true)} className="rounded-full px-6 mt-2">
              <Plus className="w-4 h-4 mr-2" />
              Write Your First Entry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Entries List with Infinite Scroll */}
      {!loading && entries.length > 0 && (
        <InfiniteScroll
          dataLength={entries.length}
          next={loadMore}
          hasMore={!!hasNextPage}
          scrollThreshold={0.9}
          loader={
            <div className="py-10 text-center">
              <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin mx-auto" />
              <p className="text-sm text-muted-foreground mt-3 font-medium animate-pulse">
                Traversing your history...
              </p>
            </div>
          }
          endMessage={
            <div className="py-12 text-center">
              <div className="w-12 h-12 bg-muted/20 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-dashed border-muted-foreground/20">
                <BookOpen className="w-6 h-6 text-muted-foreground/40" />
              </div>
              <p className="text-muted-foreground text-sm font-semibold tracking-wide uppercase opacity-60">
                End of the road - Write more to see more!
              </p>
            </div>
          }
          className="space-y-6 !overflow-visible pb-12"
        >
          {entries.map((entry, index) => (
            <motion.div
              key={entry.id}
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(index * 0.05, 0.3) }}
            >
              <JournalEntryCard
                entry={adaptEntry(entry)}
                onClick={handleEntryClick}
                variant="expanded"
              />
            </motion.div>
          ))}
        </InfiniteScroll>
      {/* Entries List */}
      {!error && entries.length > 0 && (
        <JournalListContainer
          entries={entries}
          onEntryClick={handleEntryClick}
        />
      )}

      {/* Load More / Pagination */}
      {hasNextPage && (
        <div className="flex justify-center">
          <Button
            onClick={handleLoadMore}
            disabled={loading}
            variant="outline"
            className="rounded-full px-8"
          >
            {loading ? 'Loading...' : 'Load More'}
          </Button>
        </div>
      )}
    </motion.div>
  );
}
