'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { format } from 'date-fns';
import { ArrowLeft, Save, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { TagSelector, JournalEditor } from '@/components/journal';
import { Button, Card, CardContent, useToast, EmotionIntensitySlider } from '@/components/ui';
import { journalApi } from '@/lib/api/journal';
import { JournalEntryCreate } from '@/types/journal';

const DRAFT_KEY = 'journal-draft';

interface JournalDraft extends JournalEntryCreate {
  id?: string;
  lastSaved?: string;
}

export default function NewJournalEntryPage() {
  const router = useRouter();
  const { toast } = useToast();

  const [entry, setEntry] = useState<JournalEntryCreate>({
    content: '',
    mood_rating: 5,
    tags: [],
  });

  const [energyLevel, setEnergyLevel] = useState<number | undefined>(undefined);
  const [stressLevel, setStressLevel] = useState<number | undefined>(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Load draft from localStorage on mount
  useEffect(() => {
    const savedDraft = localStorage.getItem(DRAFT_KEY);
    if (savedDraft) {
      try {
        const draft: JournalDraft = JSON.parse(savedDraft);
        setEntry({
          content: draft.content || '',
          mood_rating: draft.mood_rating || 5,
          tags: draft.tags || [],
        });
        setEnergyLevel(draft.energy_level);
        setStressLevel(draft.stress_level);
      } catch (error) {
        console.error('Failed to load draft:', error);
      }
    }
  }, []);

  // Auto-save draft to localStorage
  const saveDraft = useCallback(() => {
    const draft: JournalDraft = {
      ...entry,
      energy_level: energyLevel,
      stress_level: stressLevel,
      lastSaved: new Date().toISOString(),
    };
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  }, [entry, energyLevel, stressLevel]);

  // Auto-save on changes
  useEffect(() => {
    if (hasUnsavedChanges) {
      const timer = setTimeout(saveDraft, 1000);
      return () => clearTimeout(timer);
    }
  }, [entry, energyLevel, stressLevel, hasUnsavedChanges, saveDraft]);

  // Handle beforeunload to warn about unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  const handleContentChange = (content: string) => {
    setEntry((prev) => ({ ...prev, content }));
  };

  const handleMoodChange = (mood_rating: number) => {
    setEntry((prev) => ({ ...prev, mood_rating }));
  };

  const handleTagsChange = (tags: string[]) => {
    setEntry((prev) => ({ ...prev, tags }));
  };

  const handleSubmit = async () => {
    if (!entry.content.trim()) {
      toast({
        type: 'error',
        message: 'Please write something in your journal entry.',
      });
      return;
    }

    setIsSubmitting(true);
    try {
      // Map frontend fields to API fields
      const apiData = {
        content: entry.content,
        tags: entry.tags,
        energy_level: energyLevel,
        stress_level: stressLevel,
      };

      await journalApi.createEntry(apiData);

      // Clear draft
      localStorage.removeItem(DRAFT_KEY);

      toast({
        type: 'success',
        message: 'Journal entry saved successfully!',
      });

      // Navigate to journal list
      router.push('/journal');
    } catch (error) {
      console.error('Failed to save journal entry:', error);
      toast({
        type: 'error',
        message: 'Failed to save journal entry. Please try again.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (hasUnsavedChanges) {
      const confirmed = window.confirm('You have unsaved changes. Are you sure you want to leave?');
      if (!confirmed) return;
    }

    // Clear draft
    localStorage.removeItem(DRAFT_KEY);
    router.push('/journal');
  };

  const currentDate = format(new Date(), 'EEEE, MMMM d, yyyy');

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCancel}
                className="flex items-center gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Cancel
              </Button>
              <div>
                <h1 className="text-lg font-semibold">New Journal Entry</h1>
                <p className="text-sm text-muted-foreground">{currentDate}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Mood Slider - Prominent */}
          <Card className="overflow-hidden border-none shadow-2xl bg-white/50 dark:bg-slate-900/50 backdrop-blur-xl">
            <CardContent className="p-6 sm:p-8">
              <EmotionIntensitySlider
                value={entry.mood_rating}
                onChange={handleMoodChange}
                label="How are you feeling today?"
                type="mood"
              />
            </CardContent>
          </Card>

          {/* Journal Editor - Main Area */}
          <Card>
            <CardContent className="p-4 sm:p-6">
              <JournalEditor
                value={entry.content}
                onChange={handleContentChange}
                placeholder="What's on your mind? Write about your day, your thoughts, your feelings..."
                minHeight={300}
                maxLength={50000}
              />
            </CardContent>
          </Card>

          {/* Tags */}
          <Card>
            <CardContent className="p-4 sm:p-6">
              <TagSelector
                selected={entry.tags || []}
                onChange={handleTagsChange}
                allowCustom
                maxTags={10}
              />
            </CardContent>
          </Card>

          {/* Optional Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Energy Level */}
            <Card className="overflow-hidden border-none shadow-xl bg-white/40 dark:bg-slate-900/40 backdrop-blur-lg">
              <CardContent className="p-4 sm:p-6">
                <EmotionIntensitySlider
                  value={energyLevel || 5}
                  onChange={(value) => setEnergyLevel(value)}
                  label="Energy Level"
                  type="energy"
                  showEmoji={true}
                />
                <div className="mt-4 text-center">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setEnergyLevel(undefined)}
                    className="text-xs"
                  >
                    <X className="w-3 h-3 mr-1" />
                    Clear
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Stress Level */}
            <Card className="overflow-hidden border-none shadow-xl bg-white/40 dark:bg-slate-900/40 backdrop-blur-lg">
              <CardContent className="p-4 sm:p-6">
                <EmotionIntensitySlider
                  value={stressLevel || 5}
                  onChange={(value) => setStressLevel(value)}
                  label="Stress Level"
                  type="stress"
                  showEmoji={true}
                />
                <div className="mt-4 text-center">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setStressLevel(undefined)}
                    className="text-xs"
                  >
                    <X className="w-3 h-3 mr-1" />
                    Clear
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Save Button - Sticky Bottom */}
      <div className="sticky bottom-0 z-10 bg-background/80 backdrop-blur-sm border-t border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-end">
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting || !entry.content.trim()}
              className="flex items-center gap-2 px-8"
            >
              <Save className="w-4 h-4" />
              {isSubmitting ? 'Saving...' : 'Save Entry'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
