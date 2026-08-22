'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  HeartPulse,
  Pill,
  Briefcase,
  MessageSquareQuote,
  MapPin,
  Flame,
  Sparkles,
  Save,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronRight,
  ShieldAlert,
  UserCheck
} from 'lucide-react';
import { Button } from '@/components/ui';
import { profileApi, MentalHealthFullProfile } from '@/lib/api/profile';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface MentalHealthProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved?: (updatedProfile: MentalHealthFullProfile) => void;
}

const TABS = [
  { id: 'health', label: 'Health & Meds', icon: HeartPulse },
  { id: 'routine', label: 'Tasks & Stress', icon: Briefcase },
  { id: 'tone', label: 'Tone & Emotions', icon: MessageSquareQuote },
  { id: 'location', label: 'Location & Support', icon: MapPin },
  { id: 'incidents', label: 'Incidents & Goals', icon: Flame },
];

export function MentalHealthProfileModal({
  isOpen,
  onClose,
  onSaved,
}: MentalHealthProfileModalProps) {
  const [activeTab, setActiveTab] = useState('health');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [profile, setProfile] = useState<MentalHealthFullProfile>({
    sleep_hours: 7,
    exercise_freq: '2-3 times/week',
    dietary_patterns: 'Balanced',
    has_therapist: false,
    support_network_size: 3,
    primary_support_type: 'Friends',
    daily_task_load: 5,
    occupation: '',
    routine_habits: '',
    primary_stressors: '',
    environment_type: 'Urban',
    recent_incidents: '',
    city: '',
    country: '',
    medications: '',
    conditions: '',
    mental_health_history: '',
    preferred_tone: 'empathetic',
    common_emotions: '',
    emotional_triggers: '',
    coping_strategies: '',
    primary_goal: '',
    focus_areas: ['Self-Regulation', 'Empathy', 'Resilience'],
  });

  useEffect(() => {
    if (isOpen) {
      loadProfile();
    }
  }, [isOpen]);

  const loadProfile = async () => {
    setIsLoading(true);
    try {
      const data = await profileApi.getMentalHealthProfile();
      setProfile(data);
    } catch (err) {
      console.warn('Could not load full profile from backend, using defaults:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await profileApi.updateMentalHealthProfile(profile);
      toast.success('Mental & Emotional Health Profile updated successfully!');
      onSaved?.(profile);
      onClose();
    } catch (err: any) {
      console.error('Failed to save mental health profile:', err);
      toast.error(err?.message || 'Failed to save profile. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-background/80 backdrop-blur-md"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          className="relative w-full max-w-4xl max-h-[90vh] bg-card border border-border/80 rounded-3xl shadow-2xl overflow-hidden flex flex-col z-10"
        >
          {/* Header */}
          <div className="p-6 border-b border-border/60 bg-gradient-to-r from-primary/10 via-secondary/10 to-transparent flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-primary/20 flex items-center justify-center text-primary">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-foreground">
                  Personal Mental & Emotional Health Profile
                </h2>
                <p className="text-xs text-muted-foreground">
                  Your personalized factors directly guide our assessment questions & reflection
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-full hover:bg-muted/80 text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-border/60 overflow-x-auto no-scrollbar bg-muted/20 px-6 pt-2">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all whitespace-nowrap',
                    isActive
                      ? 'border-primary text-primary bg-primary/5 rounded-t-lg'
                      : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/40'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Body Content */}
          <div className="flex-1 overflow-y-auto p-6 sm:p-8 space-y-6">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-20 space-y-3">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Loading your health & emotional data...</p>
              </div>
            ) : (
              <>
                {/* TAB 1: Health & Meds */}
                {activeTab === 'health' && (
                  <div className="space-y-6 animate-fadeIn">
                    <div className="bg-primary/5 border border-primary/20 rounded-2xl p-4 flex items-start gap-3">
                      <HeartPulse className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                      <div className="text-xs text-muted-foreground leading-relaxed">
                        <span className="font-semibold text-foreground">Physical Vitality & Medication Factors:</span> Your sleep, energy, and medical background play a critical role in emotional regulation. Gemini uses this to calibrate resilience baselines.
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Average Sleep (Hours/Night)</label>
                        <input
                          type="number"
                          min="1"
                          max="24"
                          step="0.5"
                          value={profile.sleep_hours || ''}
                          onChange={(e) => setProfile({ ...profile, sleep_hours: parseFloat(e.target.value) || 0 })}
                          className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none"
                          placeholder="e.g. 7.5"
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Exercise Frequency</label>
                        <select
                          value={profile.exercise_freq || '2-3 times/week'}
                          onChange={(e) => setProfile({ ...profile, exercise_freq: e.target.value })}
                          className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none"
                        >
                          <option value="Daily">Daily / High Activity</option>
                          <option value="4-5 times/week">4-5 times/week</option>
                          <option value="2-3 times/week">2-3 times/week</option>
                          <option value="Once a week">Once a week</option>
                          <option value="Rarely / None">Rarely / None</option>
                        </select>
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Dietary & Nutrition Routine</label>
                        <input
                          type="text"
                          value={profile.dietary_patterns || ''}
                          onChange={(e) => setProfile({ ...profile, dietary_patterns: e.target.value })}
                          className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none"
                          placeholder="e.g. Mediterranean, Intermittent Fasting, High Protein"
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Currently Seeing a Therapist / Counselor?</label>
                        <div className="flex gap-3 pt-1">
                          <button
                            type="button"
                            onClick={() => setProfile({ ...profile, has_therapist: true })}
                            className={cn(
                              'flex-1 py-2 rounded-xl text-sm font-medium border transition-all',
                              profile.has_therapist ? 'bg-primary text-primary-foreground border-primary' : 'bg-background hover:bg-muted'
                            )}
                          >
                            Yes
                          </button>
                          <button
                            type="button"
                            onClick={() => setProfile({ ...profile, has_therapist: false })}
                            className={cn(
                              'flex-1 py-2 rounded-xl text-sm font-medium border transition-all',
                              !profile.has_therapist ? 'bg-primary text-primary-foreground border-primary' : 'bg-background hover:bg-muted'
                            )}
                          >
                            No
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-foreground">Current Medications / Supplements</label>
                      <textarea
                        value={profile.medications || ''}
                        onChange={(e) => setProfile({ ...profile, medications: e.target.value })}
                        placeholder="e.g. Sertraline 50mg, Vitamin D, Melatonin (leave blank or 'None' if applicable)"
                        rows={2}
                        className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none resize-none"
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-foreground">Mental Health & Medical History</label>
                      <textarea
                        value={profile.mental_health_history || ''}
                        onChange={(e) => setProfile({ ...profile, mental_health_history: e.target.value })}
                        placeholder="e.g. Mild generalized anxiety during exam periods, past ADHD diagnosis, insomnia"
                        rows={2}
                        className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none resize-none"
                      />
                    </div>
                  </div>
                )}

                {/* TAB 2: Routine & Stress */}
                {activeTab === 'routine' && (
                  <div className="space-y-6 animate-fadeIn">
                    <div className="bg-secondary/10 border border-secondary/20 rounded-2xl p-4 flex items-start gap-3">
                      <Briefcase className="w-5 h-5 text-secondary flex-shrink-0 mt-0.5" />
                      <div className="text-xs text-muted-foreground leading-relaxed">
                        <span className="font-semibold text-foreground">Daily Tasks & Routine Load:</span> Sharing your daily responsibilities allows the AI to tailor stress resilience assessments and examine how pressure affects decision-making.
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <label className="text-sm font-medium text-foreground">Daily Task / Workload (1-10)</label>
                          <span className="text-xs font-bold text-primary px-2 py-0.5 bg-primary/10 rounded-full">
                            {profile.daily_task_load || 5} / 10
                          </span>
                        </div>
                        <input
                          type="range"
                          min="1"
                          max="10"
                          value={profile.daily_task_load || 5}
                          onChange={(e) => setProfile({ ...profile, daily_task_load: parseInt(e.target.value) })}
                          className="w-full accent-primary"
                        />
                        <div className="flex justify-between text-[10px] text-muted-foreground">
                          <span>1 (Light)</span>
                          <span>5 (Moderate)</span>
                          <span>10 (Overwhelming)</span>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Occupation / Daily Role</label>
                        <input
                          type="text"
                          value={profile.occupation || ''}
                          onChange={(e) => setProfile({ ...profile, occupation: e.target.value })}
                          className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none"
                          placeholder="e.g. Software Engineer, Medical Student, Freelancer, Designer"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-foreground">Primary Daily Stressors</label>
                      <textarea
                        value={profile.primary_stressors || ''}
                        onChange={(e) => setProfile({ ...profile, primary_stressors: e.target.value })}
                        placeholder="e.g. Competitive exams, tight product deadlines, financial planning, family expectations"
                        rows={2}
                        className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none resize-none"
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-foreground">Daily Habits & Micro-Routines</label>
                      <textarea
                        value={profile.routine_habits || ''}
                        onChange={(e) => setProfile({ ...profile, routine_habits: e.target.value })}
                        placeholder="e.g. Morning coffee & reading, late-night screen time, midday walks, evening journaling"
                        rows={2}
                        className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none resize-none"
                      />
                    </div>
                  </div>
                )}

                {/* TAB 3: Tone & Emotions */}
                {activeTab === 'tone' && (
                  <div className="space-y-6 animate-fadeIn">
                    <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-2xl p-4 flex items-start gap-3">
                      <MessageSquareQuote className="w-5 h-5 text-indigo-500 flex-shrink-0 mt-0.5" />
                      <div className="text-xs text-muted-foreground leading-relaxed">
                        <span className="font-semibold text-foreground">AI Conversation & Journal Tone:</span> Configure how Gemini talks to you, phrases reflection questions, and approaches emotional triggers.
                      </div>
                    </div>

                    <div className="space-y-3">
                      <label className="text-sm font-medium text-foreground">Preferred AI Conversation Tone</label>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {[
                          { id: 'empathetic', title: 'Empathetic & Warm', desc: 'Gentle, validating, focus on psychological safety' },
                          { id: 'direct', title: 'Direct & Action-Oriented', desc: 'Crisp, structured, practical tools and clarity' },
                          { id: 'reflective', title: 'Reflective & Socratic', desc: 'Deep inquiry, philosophical and self-discovery' },
                          { id: 'motivational', title: 'Motivational & Uplifting', desc: 'Energizing, growth-mindset, encouraging' },
                        ].map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => setProfile({ ...profile, preferred_tone: item.id })}
                            className={cn(
                              'p-4 rounded-2xl border text-left transition-all',
                              profile.preferred_tone === item.id
                                ? 'border-primary bg-primary/10 shadow-sm'
                                : 'border-border/60 bg-background/50 hover:bg-muted/40'
                            )}
                          >
                            <div className="font-bold text-sm text-foreground">{item.title}</div>
                            <div className="text-xs text-muted-foreground mt-0.5">{item.desc}</div>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-foreground">Common Emotional States</label>
                      <input
                        type="text"
                        value={profile.common_emotions || ''}
                        onChange={(e) => setProfile({ ...profile, common_emotions: e.target.value })}
                        className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none"
                        placeholder="e.g. Calm, Restless, Overthinking, Optimistic, Fatigued"
                      />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Emotional Triggers</label>
                        <textarea
                          value={profile.emotional_triggers || ''}
                          onChange={(e) => setProfile({ ...profile, emotional_triggers: e.target.value })}
                          placeholder="e.g. Unsolicited criticism, sudden schedule changes, feeling ignored"
                          rows={2}
                          className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none resize-none"
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Coping Strategies that Work for You</label>
                        <textarea
                          value={profile.coping_strategies || ''}
                          onChange={(e) => setProfile({ ...profile, coping_strategies: e.target.value })}
                          placeholder="e.g. Box breathing, listening to lo-fi music, talking to close friend, long walks"
                          rows={2}
                          className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none resize-none"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB 4: Location & Support */}
                {activeTab === 'location' && (
                  <div className="space-y-6 animate-fadeIn">
                    <div className="bg-teal-500/10 border border-teal-500/20 rounded-2xl p-4 flex items-start gap-3">
                      <MapPin className="w-5 h-5 text-teal-500 flex-shrink-0 mt-0.5" />
                      <div className="text-xs text-muted-foreground leading-relaxed">
                        <span className="font-semibold text-foreground">Environment & Social Network:</span> Contextualizing your physical surroundings and closeness of support circles enables localized emotional nuance.
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">City / Region</label>
                        <input
                          type="text"
                          value={profile.city || ''}
                          onChange={(e) => setProfile({ ...profile, city: e.target.value })}
                          className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none"
                          placeholder="e.g. New Delhi, San Francisco, London"
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Living Environment</label>
                        <select
                          value={profile.environment_type || 'Urban'}
                          onChange={(e) => setProfile({ ...profile, environment_type: e.target.value })}
                          className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none"
                        >
                          <option value="Urban">Urban / Busy City</option>
                          <option value="Suburban">Suburban</option>
                          <option value="Rural / Quiet">Rural / Nature-proximate</option>
                          <option value="Remote / Isolated">Remote / Isolated Work</option>
                        </select>
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Close Support Network Size</label>
                        <input
                          type="number"
                          min="0"
                          max="50"
                          value={profile.support_network_size ?? 3}
                          onChange={(e) => setProfile({ ...profile, support_network_size: parseInt(e.target.value) || 0 })}
                          className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none"
                        />
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Primary Support Channel</label>
                        <select
                          value={profile.primary_support_type || 'Friends'}
                          onChange={(e) => setProfile({ ...profile, primary_support_type: e.target.value })}
                          className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none"
                        >
                          <option value="Friends">Friends</option>
                          <option value="Family">Family / Parents</option>
                          <option value="Partner/Spouse">Partner / Spouse</option>
                          <option value="Professional Support">Professional Counselor</option>
                          <option value="Community/Groups">Community / Peer Groups</option>
                        </select>
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB 5: Incidents & Goals */}
                {activeTab === 'incidents' && (
                  <div className="space-y-6 animate-fadeIn">
                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4 flex items-start gap-3">
                      <Flame className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                      <div className="text-xs text-muted-foreground leading-relaxed">
                        <span className="font-semibold text-foreground">Recent Incidents & Emotional Milestones:</span> Highlight recent life events (job shifts, relationship adjustments, personal challenges) so we will put questions targeted to your current growth chapter.
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-foreground">Recent Incidents / Significant Life Events</label>
                      <textarea
                        value={profile.recent_incidents || ''}
                        onChange={(e) => setProfile({ ...profile, recent_incidents: e.target.value })}
                        placeholder="e.g. Transitioned to a new team last month, preparing for critical entrance exam, resolved recent interpersonal conflict"
                        rows={3}
                        className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none resize-none"
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-foreground">Primary Emotional Growth Goal</label>
                      <input
                        type="text"
                        value={profile.primary_goal || ''}
                        onChange={(e) => setProfile({ ...profile, primary_goal: e.target.value })}
                        className="w-full px-4 py-2.5 rounded-xl border bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/40 focus:outline-none"
                        placeholder="e.g. Master calm decision-making under exam pressure and foster deeper empathy in my relationships"
                      />
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-border/60 bg-muted/20 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <UserCheck className="w-4 h-4 text-emerald-500" />
              <span>Encrypted & private to your personal session</span>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="outline" onClick={onClose} disabled={isSaving}>
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={isSaving || isLoading} className="gap-2">
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving Profile...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save & Apply to AI Assessments
                  </>
                )}
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
