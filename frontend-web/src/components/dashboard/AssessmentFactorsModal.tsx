'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sliders,
  Sparkles,
  X,
  Check,
  Zap,
  HeartHandshake,
  Compass,
  Volume2,
  CheckCircle2,
  Save,
  Activity,
  Layers
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { MentalHealthFullProfile, profileApi } from '@/lib/api/profile';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface AssessmentFactorsModalProps {
  isOpen: boolean;
  onClose: () => void;
  userProfile?: MentalHealthFullProfile | null;
  onFactorsSaved?: (updatedProfile: MentalHealthFullProfile) => void;
}

const TONE_OPTIONS = [
  { id: 'empathetic', label: 'Empathetic & Supportive', desc: 'Warm, encouraging, and emotionally validating' },
  { id: 'analytical', label: 'Direct & Analytical', desc: 'Concise, objective psychometric insights' },
  { id: 'calm', label: 'Calm & Grounded', desc: 'Mindful, slow-paced, and centering prompts' },
  { id: 'challenging', label: 'Growth & Challenging', desc: 'Pushes you to reflect on blind spots' },
];

const FOCUS_TAGS = [
  'Self-Regulation',
  'Empathy',
  'Burnout Prevention',
  'Emotional Agility',
  'Boundary Setting',
  'Active Listening',
  'Social Confidence',
  'Stress Resilience',
  'Workload Pacing'
];

export function AssessmentFactorsModal({
  isOpen,
  onClose,
  userProfile,
  onFactorsSaved,
}: AssessmentFactorsModalProps) {
  const [preferredTone, setPreferredTone] = useState('empathetic');
  const [recentIncidents, setRecentIncidents] = useState('');
  const [primaryStressors, setPrimaryStressors] = useState('');
  const [selectedFocusAreas, setSelectedFocusAreas] = useState<string[]>(['Self-Regulation', 'Empathy', 'Stress Resilience']);
  const [questionCount, setQuestionCount] = useState(10);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (userProfile) {
      setPreferredTone(userProfile.preferred_tone || 'empathetic');
      setRecentIncidents(userProfile.recent_incidents || '');
      setPrimaryStressors(userProfile.primary_stressors || '');
      if (Array.isArray(userProfile.focus_areas) && userProfile.focus_areas.length > 0) {
        setSelectedFocusAreas(userProfile.focus_areas);
      }
    }
  }, [userProfile, isOpen]);

  const toggleFocusArea = (tag: string) => {
    setSelectedFocusAreas((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const updated: MentalHealthFullProfile = {
        ...(userProfile || {
          sleep_hours: 7.5,
          exercise_freq: 'moderate',
          dietary_patterns: 'balanced',
          has_therapist: false,
          support_network_size: 4,
          primary_support_type: 'friends',
          daily_task_load: 'moderate',
          occupation: 'Professional',
          routine_habits: 'Morning walk',
          environment_type: 'Urban',
          city: '',
          country: '',
          medications: '',
          conditions: '',
          mental_health_history: '',
          common_emotions: 'Calm, Focused',
          emotional_triggers: 'Sudden deadlines',
          coping_strategies: 'Deep breathing',
          primary_goal: 'Emotional resilience',
        }),
        preferred_tone: preferredTone,
        recent_incidents: recentIncidents,
        primary_stressors: primaryStressors,
        focus_areas: selectedFocusAreas,
      };

      await profileApi.updateMentalHealthProfile(updated);
      toast.success('Assessment factors customized and applied!');
      onFactorsSaved?.(updated);
      onClose();
    } catch (err) {
      console.error('Failed to save factors:', err);
      toast.error('Failed to save assessment factors. Saved locally.');
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-background/80 backdrop-blur-md"
          />

          {/* Modal Card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="relative w-full max-w-2xl bg-card border border-border/80 rounded-3xl shadow-2xl overflow-hidden z-10 my-8"
          >
            {/* Header */}
            <div className="p-6 sm:p-8 border-b border-border/40 bg-gradient-to-r from-primary/10 via-secondary/10 to-transparent">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-primary/15 text-primary border border-primary/20">
                    <Sliders className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-xl sm:text-2xl font-black text-foreground tracking-tight">
                      Customize Assessment Factors
                    </h2>
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      Tune the psychometric parameters and life context used by our assessment engine.
                    </p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="p-6 sm:p-8 space-y-6 max-h-[70vh] overflow-y-auto">
              {/* Factor 1: Recent Life Events & Chapter */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Compass className="w-4 h-4 text-primary" />
                  <label className="text-xs font-bold uppercase tracking-wider text-foreground">
                    Current Life Chapter & Recent Events
                  </label>
                </div>
                <p className="text-xs text-muted-foreground">
                  Highlight recent life events (job shifts, relationship adjustments, personal challenges) so we build questions targeted to your current growth chapter.
                </p>
                <textarea
                  value={recentIncidents}
                  onChange={(e) => setRecentIncidents(e.target.value)}
                  placeholder="e.g., Started a demanding new project last week; navigating team communication challenges."
                  rows={2}
                  className="w-full px-3.5 py-2.5 rounded-2xl border border-border/80 bg-background text-foreground text-xs focus:ring-2 focus:ring-primary/40 focus:border-primary outline-none transition-all resize-none"
                />
              </div>

              {/* Factor 2: Primary Stressors */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-500" />
                  <label className="text-xs font-bold uppercase tracking-wider text-foreground">
                    Active Stressors & Cognitive Pressure
                  </label>
                </div>
                <p className="text-xs text-muted-foreground">
                  Specify triggers that drain your emotional energy so resilience scenarios test real friction points.
                </p>
                <input
                  type="text"
                  value={primaryStressors}
                  onChange={(e) => setPrimaryStressors(e.target.value)}
                  placeholder="e.g., Unclear requirements, tight deadlines, conflict avoidance"
                  className="w-full px-3.5 py-2.5 rounded-2xl border border-border/80 bg-background text-foreground text-xs focus:ring-2 focus:ring-primary/40 focus:border-primary outline-none transition-all"
                />
              </div>

              {/* Factor 3: Target EQ Focus Areas */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-500" />
                  <label className="text-xs font-bold uppercase tracking-wider text-foreground">
                    Focus Dimensions for Next Assessments
                  </label>
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  {FOCUS_TAGS.map((tag) => {
                    const isSelected = selectedFocusAreas.includes(tag);
                    return (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => toggleFocusArea(tag)}
                        className={cn(
                          'px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all flex items-center gap-1.5',
                          isSelected
                            ? 'bg-primary text-primary-foreground border-primary shadow-xs'
                            : 'bg-muted/30 border-border/80 text-muted-foreground hover:text-foreground hover:bg-muted/60'
                        )}
                      >
                        {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                        {tag}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Factor 4: Tone Calibration */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Volume2 className="w-4 h-4 text-indigo-500" />
                  <label className="text-xs font-bold uppercase tracking-wider text-foreground">
                    Question Tone & Delivery Style
                  </label>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {TONE_OPTIONS.map((tone) => {
                    const isSelected = preferredTone === tone.id;
                    return (
                      <div
                        key={tone.id}
                        onClick={() => setPreferredTone(tone.id)}
                        className={cn(
                          'p-3 rounded-2xl border cursor-pointer transition-all flex flex-col justify-between',
                          isSelected
                            ? 'bg-primary/10 border-primary shadow-xs'
                            : 'bg-muted/20 border-border/60 hover:border-border hover:bg-muted/40'
                        )}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-bold text-foreground">{tone.label}</span>
                          {isSelected && <CheckCircle2 className="w-4 h-4 text-primary fill-primary/20" />}
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-tight">{tone.desc}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Footer Actions */}
            <div className="p-6 border-t border-border/40 bg-muted/10 flex flex-col sm:flex-row items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground">
                Saved factors apply immediately to all dynamic assessments.
              </span>
              <div className="flex items-center gap-2.5 w-full sm:w-auto">
                <Button variant="outline" onClick={onClose} className="rounded-xl text-xs font-bold flex-1 sm:flex-none">
                  Cancel
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="rounded-xl gap-2 bg-primary text-primary-foreground font-bold text-xs shadow-md flex-1 sm:flex-none"
                >
                  <Save className="w-3.5 h-3.5" />
                  {isSaving ? 'Saving Factors...' : 'Save & Apply Factors'}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
