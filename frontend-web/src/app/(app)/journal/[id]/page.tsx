'use client';

import React, { useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useApi } from '@/hooks/useApi';
import { journalApi, JournalEntry, CreateJournalEntry } from '@/lib/api/journal';
import { ErrorDisplay, Skeleton } from '@/components/common';
import { Button, Card, CardContent, Input, EmotionIntensitySlider } from '@/components/ui';
import {
  ArrowLeft,
  Calendar,
  Tag,
  Edit,
  Trash2,
  Smile,
  Meh,
  Frown,
  Sparkles,
  X,
  Share2,
  Battery,
  Zap,
  Brain,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

const MOOD_ICONS = {
  positive: { icon: Smile, color: 'text-green-500', bg: 'bg-green-500/10' },
  neutral: { icon: Meh, color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
  negative: { icon: Frown, color: 'text-red-500', bg: 'bg-red-500/10' },
};

const MOOD_LABELS = [
  'Very Low',
  'Low',
  'Neutral',
  'Good',
  'Great',
  'Excellent',
  'Amazing',
  'Fantastic',
  'Outstanding',
  'Perfect',
];

function getMoodCategory(score?: number) {
  if (score == null) return 'neutral';
  if (score >= 7) return 'positive';
  if (score >= 4) return 'neutral';
  return 'negative';
}

function getSentimentLabel(score?: number) {
  if (score == null) return 'Neutral';
  if (score > 0.3) return 'Positive';
  if (score < -0.3) return 'Negative';
  return 'Neutral';
}

function getSentimentColor(score?: number) {
  if (score == null) return 'text-gray-500';
  if (score > 0.3) return 'text-green-600';
  if (score < -0.3) return 'text-red-600';
  return 'text-yellow-600';
}

export default function JournalEntryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = parseInt(params.id as string);
  const [isEditing, setIsEditing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    data: entry,
    loading,
    error,
    refetch,
  } = useApi({
    apiFn: () => journalApi.getEntry(id),
    deps: [id],
  });

  const [editForm, setEditForm] = useState<CreateJournalEntry>({
    title: '',
    content: '',
    tags: [],
    mood_rating: undefined,
    energy_level: undefined,
    stress_level: undefined,
  });
  const [tagInput, setTagInput] = useState('');

  // Initialize edit form when entry loads
  React.useEffect(() => {
    if (entry && !isEditing) {
      setEditForm({
        title: entry.title || '',
        content: entry.content,
        tags: entry.tags || [],
        mood_rating: entry.mood_rating || entry.mood_score,
        energy_level: entry.energy_level,
        stress_level: entry.stress_level,
      });
    }
  }, [entry, isEditing]);

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    if (entry) {
      setEditForm({
        title: entry.title || '',
        content: entry.content,
        tags: entry.tags || [],
        mood_rating: entry.mood_rating || entry.mood_score,
        energy_level: entry.energy_level,
        stress_level: entry.stress_level,
      });
    }
  };

  const handleSaveEdit = useCallback(async () => {
    if (!editForm.content.trim()) return;
    setIsSubmitting(true);
    try {
      await journalApi.updateEntry(id, editForm);
      setIsEditing(false);
      refetch();
    } catch {
      // TODO: toast
    } finally {
      setIsSubmitting(false);
    }
  }, [editForm, id, refetch]);

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this entry? This action cannot be undone.')) {
      try {
        await journalApi.deleteEntry(id);
        router.push('/journal');
      } catch {
        // TODO: toast
      }
    }
  };

  const handleShare = async () => {
    if (navigator.share && entry) {
      try {
        await navigator.share({
          title: entry.title || 'Journal Entry',
          text: entry.content.substring(0, 100) + (entry.content.length > 100 ? '...' : ''),
          url: window.location.href,
        });
      } catch {
        // Fallback to clipboard
        navigator.clipboard.writeText(window.location.href);
        // TODO: toast success
      }
    } else {
      // Fallback to clipboard
      navigator.clipboard.writeText(window.location.href);
      // TODO: toast success
    }
  };

  const handleAddTag = () => {
    const tag = tagInput.trim().toLowerCase();
    if (tag && !editForm.tags?.includes(tag)) {
      setEditForm((prev) => ({ ...prev, tags: [...(prev.tags || []), tag] }));
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setEditForm((prev) => ({ ...prev, tags: prev.tags?.filter((t) => t !== tag) }));
  };

  const formatDate = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <Skeleton className="h-8 w-48" />
        <Card className="rounded-[2rem]">
          <CardContent className="p-8 space-y-4">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return <ErrorDisplay message={error} onRetry={refetch} />;
  }

  if (!entry) {
    return (
      <div className="max-w-4xl mx-auto text-center py-12">
        <h1 className="text-2xl font-bold">Entry not found</h1>
        <Link href="/journal">
          <Button className="mt-4">Back to Journal</Button>
        </Link>
      </div>
    );
  }

  const mood = getMoodCategory(entry.mood_rating || entry.mood_score);
  const MoodIcon = MOOD_ICONS[mood].icon;
  const moodLabel = entry.mood_rating ? MOOD_LABELS[entry.mood_rating - 1] : 'Not rated';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="max-w-4xl mx-auto space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <Link href="/journal">
          <Button variant="ghost" className="rounded-full">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Journal
          </Button>
        </Link>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleShare} className="rounded-full">
            <Share2 className="w-4 h-4 mr-2" />
            Share
          </Button>
          {!isEditing && (
            <>
              <Button variant="outline" onClick={handleEdit} className="rounded-full">
                <Edit className="w-4 h-4 mr-2" />
                Edit
              </Button>
              <Button
                variant="outline"
                onClick={handleDelete}
                className="rounded-full text-red-500 hover:text-red-600"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Edit Mode */}
      <AnimatePresence>
        {isEditing && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="rounded-[2rem] border-none bg-background/60 backdrop-blur-xl shadow-xl shadow-black/5 overflow-hidden">
              <CardContent className="p-8 space-y-6">
                <div className="flex items-center gap-2 text-primary">
                  <Sparkles className="w-5 h-5" />
                  <span className="text-sm font-bold uppercase tracking-wider">
                    Edit Journal Entry
                  </span>
                </div>

                <Input
                  type="text"
                  placeholder="Title (optional)"
                  value={editForm.title}
                  onChange={(e) => setEditForm((prev) => ({ ...prev, title: e.target.value }))}
                  className="rounded-xl text-lg font-medium"
                />

                <textarea
                  placeholder="What's on your mind today?"
                  value={editForm.content}
                  onChange={(e) => setEditForm((prev) => ({ ...prev, content: e.target.value }))}
                  rows={8}
                  className="w-full px-4 py-3 rounded-xl border bg-muted/30 text-sm leading-relaxed resize-none focus:ring-2 focus:ring-primary/40 outline-none transition-all placeholder:text-muted-foreground/60"
                />

                {/* Mood Rating */}
                <div className="space-y-3">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Smile className="w-4 h-4" />
                    Mood Rating
                  </label>
                  <div className="flex items-center gap-4">
                    <EmotionIntensitySlider
                      value={editForm.mood_rating || 5}
                      onChange={(value) => setEditForm((prev) => ({ ...prev, mood_rating: value }))}
                      max={10}
                      min={1}
                      step={1}
                      type="mood"
                      className="flex-1"
                    />
                    <div className="flex items-center gap-2 min-w-[100px]">
                      <span className="text-sm font-medium">
                        {MOOD_LABELS[(editForm.mood_rating || 5) - 1]}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        ({editForm.mood_rating || 5}/10)
                      </span>
                    </div>
                  </div>
                </div>

                {/* Energy Level */}
                <div className="space-y-3">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Battery className="w-4 h-4" />
                    Energy Level
                  </label>
                  <div className="flex items-center gap-4">
                    <EmotionIntensitySlider
                      value={editForm.energy_level || 5}
                      onChange={(value) =>
                        setEditForm((prev) => ({ ...prev, energy_level: value }))
                      }
                      max={10}
                      min={1}
                      step={1}
                      type="energy"
                      className="flex-1"
                    />
                    <div className="flex items-center gap-2 min-w-[60px]">
                      <span className="text-sm font-medium">{editForm.energy_level || 5}/10</span>
                    </div>
                  </div>
                </div>

                {/* Stress Level */}
                <div className="space-y-3">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Zap className="w-4 h-4" />
                    Stress Level
                  </label>
                  <div className="flex items-center gap-4">
                    <EmotionIntensitySlider
                      value={editForm.stress_level || 5}
                      onChange={(value) =>
                        setEditForm((prev) => ({ ...prev, stress_level: value }))
                      }
                      max={10}
                      min={1}
                      step={1}
                      type="stress"
                      className="flex-1"
                    />
                    <div className="flex items-center gap-2 min-w-[60px]">
                      <span className="text-sm font-medium">{editForm.stress_level || 5}/10</span>
                    </div>
                  </div>
                </div>

                {/* Tags */}
                <div className="space-y-3">
                  <label className="text-sm font-medium flex items-center gap-2">
                    <Tag className="w-4 h-4" />
                    Tags
                  </label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="text"
                      placeholder="Add a tag and press Enter"
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                      className="flex-1 rounded-lg"
                    />
                  </div>
                  {(editForm.tags?.length ?? 0) > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {editForm.tags?.map((tag) => (
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
                  <Button variant="outline" onClick={handleCancelEdit} className="rounded-full">
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSaveEdit}
                    disabled={isSubmitting || !editForm.content.trim()}
                    className="rounded-full px-6 shadow-lg shadow-primary/20"
                  >
                    {isSubmitting ? (
                      <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin mr-2" />
                    ) : null}
                    {isSubmitting ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* View Mode */}
      {!isEditing && (
        <Card className="rounded-[2rem] border-none bg-background/60 backdrop-blur-xl shadow-xl shadow-black/5">
          <CardContent className="p-8 space-y-6">
            {/* Title & Date */}
            <div className="space-y-4">
              <h1 className="text-3xl font-bold">{entry.title || 'Untitled Entry'}</h1>
              <div className="flex items-center gap-3 text-muted-foreground">
                <Calendar className="w-5 h-5" />
                <span className="text-lg">
                  {formatDate(entry.timestamp || entry.created_at || new Date().toISOString())}
                </span>
              </div>
            </div>

            {/* Mood & Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6 bg-muted/30 rounded-2xl">
              <div className="text-center space-y-2">
                <div className={`p-3 rounded-xl ${MOOD_ICONS[mood].bg} w-fit mx-auto`}>
                  <MoodIcon className={`w-6 h-6 ${MOOD_ICONS[mood].color}`} />
                </div>
                <div className="text-sm font-medium">Mood</div>
                <div className="text-xs text-muted-foreground">
                  {moodLabel}
                  {entry.mood_rating && ` (${entry.mood_rating}/10)`}
                </div>
              </div>

              {entry.energy_level && (
                <div className="text-center space-y-2">
                  <div className="p-3 rounded-xl bg-blue-500/10 w-fit mx-auto">
                    <Battery className="w-6 h-6 text-blue-500" />
                  </div>
                  <div className="text-sm font-medium">Energy</div>
                  <div className="text-xs text-muted-foreground">{entry.energy_level}/10</div>
                </div>
              )}

              {entry.stress_level && (
                <div className="text-center space-y-2">
                  <div className="p-3 rounded-xl bg-orange-500/10 w-fit mx-auto">
                    <Zap className="w-6 h-6 text-orange-500" />
                  </div>
                  <div className="text-sm font-medium">Stress</div>
                  <div className="text-xs text-muted-foreground">{entry.stress_level}/10</div>
                </div>
              )}
            </div>

            {/* Sentiment Analysis */}
            {entry.sentiment_score !== undefined && (
              <div className="flex items-center gap-3 p-4 bg-muted/20 rounded-xl">
                <Brain className="w-5 h-5 text-primary" />
                <div className="flex-1">
                  <div className="text-sm font-medium">Sentiment Analysis</div>
                  <div className={`text-sm ${getSentimentColor(entry.sentiment_score)}`}>
                    {getSentimentLabel(entry.sentiment_score)} (
                    {entry.sentiment_score > 0 ? '+' : ''}
                    {(entry.sentiment_score * 100).toFixed(0)}%)
                  </div>
                </div>
                {entry.sentiment_score > 0 ? (
                  <TrendingUp className="w-5 h-5 text-green-500" />
                ) : entry.sentiment_score < 0 ? (
                  <TrendingDown className="w-5 h-5 text-red-500" />
                ) : (
                  <Minus className="w-5 h-5 text-yellow-500" />
                )}
              </div>
            )}

            {/* AI Patterns */}
            {entry.patterns && entry.patterns.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-primary">
                  <Sparkles className="w-5 h-5" />
                  <span className="text-sm font-bold uppercase tracking-wider">
                    Detected Patterns
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {entry.patterns.map((pattern, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium"
                    >
                      {pattern}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Content */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Entry</h3>
              <div className="prose prose-lg max-w-none">
                <p className="text-foreground leading-relaxed whitespace-pre-wrap text-lg">
                  {entry.content}
                </p>
              </div>
            </div>

            {/* Tags */}
            {entry.tags && entry.tags.length > 0 && (
              <div className="space-y-3 pt-4 border-t">
                <h3 className="text-lg font-semibold">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {entry.tags.map((tag) => (
                    <span
                      key={tag}
                      className="flex items-center gap-1 px-3 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium"
                    >
                      <Tag className="w-4 h-4" />#{tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}
