'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  Brain,
  Zap,
  Users2,
  Compass,
  Flame,
  ArrowRight,
  CheckCircle2,
  Award,
  RefreshCw,
  Sliders,
  Play,
  HeartPulse,
  Settings2,
  X,
  Loader2,
  ChevronRight,
  TrendingUp,
  ShieldCheck,
  RotateCcw,
  Clock,
  Activity
} from 'lucide-react';
import { Button } from '@/components/ui';
import { questionsApi, Question } from '@/lib/api/questions';
import { MentalHealthFullProfile } from '@/lib/api/profile';
import { AssessmentFactorsModal } from './AssessmentFactorsModal';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface PersonalizedAssessmentHubProps {
  userProfile?: MentalHealthFullProfile | null;
  onOpenProfileEditor?: () => void;
  onProfileUpdated?: (profile: MentalHealthFullProfile) => void;
}

interface AssessmentTypeCard {
  id: string;
  title: string;
  badge: string;
  description: string;
  icon: React.ElementType;
  gradient: string;
  borderHover: string;
  estimatedMinutes: number;
  highlightFactors: string[];
}

const ASSESSMENT_TYPES: AssessmentTypeCard[] = [
  {
    id: 'holistic_eq',
    title: 'Holistic Emotional Intelligence',
    badge: 'Comprehensive',
    description: 'A 5-dimensional evaluation covering Self-Awareness, Self-Regulation, Motivation, Empathy, and Social Skills.',
    icon: Brain,
    gradient: 'from-blue-500/10 via-indigo-500/5 to-transparent',
    borderHover: 'hover:border-blue-500/50',
    estimatedMinutes: 5,
    highlightFactors: ['5 Core EQ Domains', 'Daniel Goleman Model', 'Benchmark Baseline']
  },
  {
    id: 'stress_resilience',
    title: 'Stress & Task Resilience',
    badge: 'Personalized to Routine',
    description: 'Calibrated to your daily task workload, routine habits, and primary stressors to measure burnout resistance.',
    icon: Zap,
    gradient: 'from-amber-500/10 via-orange-500/5 to-transparent',
    borderHover: 'hover:border-amber-500/50',
    estimatedMinutes: 4,
    highlightFactors: ['Workload Pacing', 'Cognitive Fatigue', 'Stress Responses']
  },
  {
    id: 'relationships_empathy',
    title: 'Relationships & Social Empathy',
    badge: 'Social Circle Calibrated',
    description: 'Assesses interpersonal resonance, active listening, boundary management, and social support synergy.',
    icon: Users2,
    gradient: 'from-emerald-500/10 via-teal-500/5 to-transparent',
    borderHover: 'hover:border-emerald-500/50',
    estimatedMinutes: 4,
    highlightFactors: ['Support Network', 'Conflict Nav', 'Empathic Accuracy']
  },
  {
    id: 'reflection_triggers',
    title: 'Emotional Triggers & Incidents',
    badge: 'Deep Reflection',
    description: 'Tailored around recent life events, known emotional triggers, and coping strategy effectiveness.',
    icon: Compass,
    gradient: 'from-purple-500/10 via-pink-500/5 to-transparent',
    borderHover: 'hover:border-purple-500/50',
    estimatedMinutes: 5,
    highlightFactors: ['Trigger Sensitivity', 'Coping Efficacy', 'Self-Compassion']
  },
  {
    id: 'personalized_custom',
    title: 'Gemini AI Dynamic Custom Assessment',
    badge: 'Gemini 2.5 Flash',
    description: 'Real-time psychometric generation that completely synthesizes your health, medications, routine, and preferred tone.',
    icon: Sparkles,
    gradient: 'from-primary/20 via-secondary/10 to-transparent',
    borderHover: 'hover:border-primary',
    estimatedMinutes: 3,
    highlightFactors: ['Full Profile Synthesis', 'Instant Gemini Generation', 'Tone-Adaptive']
  }
];

export function PersonalizedAssessmentHub({
  userProfile,
  onOpenProfileEditor,
  onProfileUpdated,
}: PersonalizedAssessmentHubProps) {
  // Assessment Runner state
  const [activeAssessment, setActiveAssessment] = useState<AssessmentTypeCard | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQIndex, setCurrentQIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [isCompleted, setIsCompleted] = useState(false);
  const [questionCount, setQuestionCount] = useState<number>(10);
  const [isFactorsModalOpen, setIsFactorsModalOpen] = useState(false);

  const startAssessment = async (card: AssessmentTypeCard) => {
    setActiveAssessment(card);
    setIsGenerating(true);
    setIsCompleted(false);
    setCurrentQIndex(0);
    setAnswers({});

    try {
      const response = await questionsApi.generatePersonalizedAssessment({
        user_context: userProfile || {},
        assessment_type: card.id,
        count: questionCount,
        tone: userProfile?.preferred_tone || 'empathetic',
      });

      if (response.questions && response.questions.length > 0) {
        setQuestions(response.questions);
        toast.success(`Generated ${response.questions.length} questions tailored to your profile!`);
      } else {
        throw new Error('No questions received from generator');
      }
    } catch (err: any) {
      console.warn('Personalized generation failed, falling back to standard bank:', err);
      try {
        const fallback = await questionsApi.getQuestions({ count: questionCount });
        setQuestions(fallback.questions);
      } catch (fErr: any) {
        toast.error('Failed to load assessment. Please check backend connection.');
        setActiveAssessment(null);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSelectOption = (value: number) => {
    const currentQ = questions[currentQIndex];
    if (!currentQ) return;

    const newAnswers = { ...answers, [currentQ.id]: value };
    setAnswers(newAnswers);

    if (currentQIndex < questions.length - 1) {
      setTimeout(() => {
        setCurrentQIndex(prev => prev + 1);
      }, 150);
    } else {
      setTimeout(() => {
        setIsCompleted(true);
      }, 200);
    }
  };

  // Calculate score breakdown (4-point forced-choice scale: 1=Strongly Disagree to 4=Strongly Agree)
  const calculateResults = () => {
    const totalScore = Object.values(answers).reduce((sum, v) => sum + v, 0);
    const maxScore = questions.length * 4;
    const percentage = Math.round((totalScore / (maxScore || 1)) * 100);

    const categoryScores: Record<string, { sum: number; count: number }> = {};
    questions.forEach((q) => {
      const cat = q.category || 'Core EQ';
      if (!categoryScores[cat]) categoryScores[cat] = { sum: 0, count: 0 };
      if (answers[q.id]) {
        categoryScores[cat].sum += answers[q.id];
        categoryScores[cat].count += 1;
      }
    });

    const categoryPercentages = Object.entries(categoryScores).map(([category, { sum, count }]) => ({
      category,
      percentage: count > 0 ? Math.round((sum / (count * 4)) * 100) : 0,
    }));

    return { totalScore, maxScore, percentage, categoryPercentages };
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl border border-primary/20 bg-gradient-to-r from-primary/10 via-secondary/10 to-card p-6 sm:p-8 backdrop-blur-xl">
        <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-2 max-w-xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/15 border border-primary/30 text-xs font-semibold text-primary">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Gemini 2.5 Flash Psychometric Engine</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground tracking-tight">
              Personalized Assessment Hub
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Explore scientifically structured emotional assessments dynamically tailored to your daily task load, health vitality, medications, emotional triggers, and preferred tone.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              onClick={() => setIsFactorsModalOpen(true)}
              variant="outline"
              className="gap-2 rounded-2xl border-primary/30 hover:bg-primary/10 hover:text-primary transition-all shadow-sm"
            >
              <Sliders className="w-4 h-4" />
              <span>Customize Personal Factors</span>
            </Button>
          </div>
        </div>

        {/* Ambient Glow */}
        <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-primary/20 blur-3xl pointer-events-none" />
      </div>

      {/* Assessment Option Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {ASSESSMENT_TYPES.map((card, index) => {
          const Icon = card.icon;
          const isGeminiCustom = card.id === 'personalized_custom';

          return (
            <motion.div
              key={card.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08 }}
              className={cn(
                'group relative rounded-3xl border bg-card/60 p-6 backdrop-blur-md transition-all duration-300 flex flex-col justify-between hover:shadow-xl hover:-translate-y-1',
                card.borderHover,
                isGeminiCustom ? 'md:col-span-2 lg:col-span-2 border-primary/40 bg-gradient-to-br from-primary/10 via-card to-secondary/5' : 'border-border/60'
              )}
            >
              <div className="space-y-4">
                {/* Top Badge & Icon */}
                <div className="flex items-center justify-between">
                  <div className={cn(
                    'w-12 h-12 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110 duration-300',
                    isGeminiCustom ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/25' : 'bg-primary/10 text-primary'
                  )}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className={cn(
                    'text-[11px] font-semibold px-3 py-1 rounded-full border',
                    isGeminiCustom
                      ? 'bg-primary/20 text-primary border-primary/30'
                      : 'bg-muted/80 text-muted-foreground border-border/40'
                  )}>
                    {card.badge}
                  </span>
                </div>

                {/* Title & Description */}
                <div>
                  <h3 className="text-lg font-bold text-foreground group-hover:text-primary transition-colors">
                    {card.title}
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
                    {card.description}
                  </p>
                </div>

                {/* Highlight Tags */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {card.highlightFactors.map((tag) => (
                    <span
                      key={tag}
                      className="text-[10px] font-medium px-2 py-0.5 rounded-lg bg-background/80 border border-border/50 text-foreground/80"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Card Footer & Action Button */}
              <div className="pt-4 border-t border-border/40 mt-5 space-y-3">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <div className="flex items-center gap-1.5 font-semibold text-[11px]">
                    <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                    <span>~{card.estimatedMinutes} mins</span>
                    <span className="text-border">•</span>
                    <span>{questionCount} Questions</span>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-primary/80">
                    {isGeminiCustom ? 'AI Tailored' : 'Standard Baseline'}
                  </span>
                </div>

                <Button
                  onClick={() => startAssessment(card)}
                  className={cn(
                    'w-full h-11 rounded-2xl font-bold text-xs uppercase tracking-wider transition-all duration-300 flex items-center justify-between px-4 shadow-sm group/btn cursor-pointer',
                    isGeminiCustom
                      ? 'bg-gradient-to-r from-primary via-indigo-500 to-purple-600 hover:opacity-95 text-white shadow-lg shadow-primary/25 hover:scale-[1.01]'
                      : 'bg-primary/10 hover:bg-primary text-primary hover:text-primary-foreground border border-primary/20 hover:border-primary group-hover:bg-primary group-hover:text-primary-foreground'
                  )}
                >
                  <div className="flex items-center gap-2">
                    {isGeminiCustom ? (
                      <Sparkles className="w-4 h-4 fill-white/20 shrink-0" />
                    ) : (
                      <Activity className="w-4 h-4 shrink-0" />
                    )}
                    <span className="truncate">{isGeminiCustom ? 'Start Custom Assessment' : 'Start Assessment'}</span>
                  </div>
                  <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover/btn:translate-x-1 shrink-0" />
                </Button>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Assessment Runner Modal */}
      <AnimatePresence>
        {activeAssessment && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => !isGenerating && setActiveAssessment(null)}
              className="fixed inset-0 bg-background/85 backdrop-blur-md"
            />

            {/* Modal Content */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-2xl bg-card border border-border/80 rounded-3xl shadow-2xl overflow-hidden z-10 flex flex-col max-h-[90vh]"
            >
              {/* Modal Header */}
              <div className="p-6 border-b border-border/60 bg-muted/20 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-primary/20 text-primary flex items-center justify-center">
                    <activeAssessment.icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-foreground text-lg">
                      {activeAssessment.title}
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      Personalized AI Psychometric Examination
                    </p>
                  </div>
                </div>

                {!isGenerating && (
                  <button
                    onClick={() => setActiveAssessment(null)}
                    className="p-2 rounded-full hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                )}
              </div>

              {/* Modal Body */}
              <div className="p-6 sm:p-8 flex-1 overflow-y-auto">
                {isGenerating ? (
                  <div className="flex flex-col items-center justify-center py-16 space-y-4 text-center">
                    <div className="relative">
                      <Loader2 className="w-12 h-12 animate-spin text-primary" />
                      <Sparkles className="w-5 h-5 text-amber-500 absolute -top-1 -right-1 animate-pulse" />
                    </div>
                    <div>
                      <h4 className="font-bold text-foreground text-base">
                        Generating Personalized Questions with Gemini 2.5 Flash...
                      </h4>
                      <p className="text-xs text-muted-foreground max-w-md mt-1">
                        Synthesizing your health, daily routine, emotional triggers, and preferred tone for precise psychological relevance.
                      </p>
                    </div>
                  </div>
                ) : isCompleted ? (
                  /* Results View */
                  <div className="space-y-6 animate-fadeIn">
                    {(() => {
                      const results = calculateResults();
                      return (
                        <>
                          <div className="text-center space-y-2">
                            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 mb-2">
                              <Award className="w-8 h-8" />
                            </div>
                            <h4 className="text-2xl font-black text-foreground">
                              Assessment Completed!
                            </h4>
                            <p className="text-xs text-muted-foreground max-w-md mx-auto">
                              Here is your personalized emotional intelligence breakdown based on your contextual responses:
                            </p>
                          </div>

                          {/* Overall Score Card */}
                          <div className="p-6 rounded-3xl bg-gradient-to-r from-primary/10 via-secondary/10 to-transparent border border-primary/20 flex items-center justify-between">
                            <div>
                              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                Overall EQ Index
                              </div>
                              <div className="text-4xl font-extrabold text-foreground mt-1">
                                {results.percentage}%
                              </div>
                              <div className="text-xs text-muted-foreground mt-1">
                                Score: {results.totalScore} / {results.maxScore}
                              </div>
                            </div>

                            <div className="text-right">
                              <div className={cn(
                                'inline-block px-3 py-1 rounded-full text-xs font-bold border',
                                results.percentage >= 75
                                  ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30'
                                  : results.percentage >= 50
                                    ? 'bg-blue-500/10 text-blue-500 border-blue-500/30'
                                    : 'bg-amber-500/10 text-amber-500 border-amber-500/30'
                              )}>
                                {results.percentage >= 75 ? 'Optimal Resilience' : results.percentage >= 50 ? 'Developing Mastery' : 'High Growth Potential'}
                              </div>
                            </div>
                          </div>

                          {/* Dimension Breakdown */}
                          <div className="space-y-3">
                            <h5 className="text-sm font-bold text-foreground flex items-center gap-2">
                              <TrendingUp className="w-4 h-4 text-primary" />
                              <span>Domain Breakdown</span>
                            </h5>

                            <div className="space-y-2.5">
                              {results.categoryPercentages.map((cat) => (
                                <div key={cat.category} className="p-3 rounded-2xl bg-muted/30 border border-border/40 space-y-1.5">
                                  <div className="flex justify-between text-xs font-medium text-foreground">
                                    <span>{cat.category}</span>
                                    <span className="font-bold text-primary">{cat.percentage}%</span>
                                  </div>
                                  <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-primary rounded-full transition-all duration-700"
                                      style={{ width: `${cat.percentage}%` }}
                                    />
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Action Buttons */}
                          <div className="pt-4 flex items-center gap-3">
                            <Button
                              onClick={() => startAssessment(activeAssessment)}
                              variant="outline"
                              className="flex-1 gap-2 rounded-xl"
                            >
                              <RotateCcw className="w-4 h-4" />
                              <span>Retake</span>
                            </Button>
                            <Button
                              onClick={() => setActiveAssessment(null)}
                              className="flex-1 gap-2 rounded-xl"
                            >
                              <CheckCircle2 className="w-4 h-4" />
                              <span>Done & Return to Dashboard</span>
                            </Button>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                ) : questions.length > 0 ? (
                  /* Question Answering View */
                  <div className="space-y-6">
                    {/* Progress Bar */}
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs font-medium text-muted-foreground">
                        <span>Question {currentQIndex + 1} of {questions.length}</span>
                        <span className="text-primary font-bold">{Math.round(((currentQIndex + 1) / questions.length) * 100)}%</span>
                      </div>
                      <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all duration-300"
                          style={{ width: `${((currentQIndex + 1) / questions.length) * 100}%` }}
                        />
                      </div>
                    </div>

                    {/* Category Tag */}
                    <div className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
                      {questions[currentQIndex]?.category || 'Emotional Reflection'}
                    </div>

                    {/* Question Statement */}
                    <div className="p-6 rounded-3xl bg-muted/20 border border-border/60 min-h-[110px] flex items-center">
                      <p className="text-base sm:text-lg font-semibold text-foreground leading-relaxed">
                        &ldquo;{questions[currentQIndex]?.text}&rdquo;
                      </p>
                    </div>

                    {/* Likert Scale Options (1-4 Forced Choice: No Neutral) */}
                    <div className="space-y-2.5">
                      <div className="text-xs font-semibold text-muted-foreground text-center">
                        Rate how accurately this statement describes you:
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        {[
                          { val: 1, label: 'Strongly Disagree', short: '1' },
                          { val: 2, label: 'Disagree', short: '2' },
                          { val: 3, label: 'Agree', short: '3' },
                          { val: 4, label: 'Strongly Agree', short: '4' },
                        ].map((opt) => {
                          const isSelected = answers[questions[currentQIndex]?.id] === opt.val;
                          return (
                            <button
                              key={opt.val}
                              onClick={() => handleSelectOption(opt.val)}
                              className={cn(
                                'p-3.5 rounded-2xl border text-center transition-all flex flex-col items-center justify-center gap-1 hover:scale-105 active:scale-95 cursor-pointer',
                                isSelected
                                  ? 'bg-primary text-primary-foreground border-primary shadow-md'
                                  : 'bg-card border-border/80 hover:border-primary/50 hover:bg-muted/40 text-foreground'
                              )}
                            >
                              <span className="text-lg font-black">{opt.short}</span>
                              <span className="text-[11px] font-bold leading-tight uppercase tracking-wider">{opt.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Question Navigation */}
                    <div className="flex justify-between items-center pt-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={currentQIndex === 0}
                        onClick={() => setCurrentQIndex(prev => Math.max(0, prev - 1))}
                        className="text-xs text-muted-foreground"
                      >
                        Previous Statement
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={currentQIndex >= questions.length - 1}
                        onClick={() => setCurrentQIndex(prev => Math.min(questions.length - 1, prev + 1))}
                        className="text-xs text-primary"
                      >
                        Next Statement
                      </Button>
                    </div>
                  </div>
                ) : null}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Dedicated Assessment Factors Customizer Modal */}
      <AssessmentFactorsModal
        isOpen={isFactorsModalOpen}
        onClose={() => setIsFactorsModalOpen(false)}
        userProfile={userProfile}
        onFactorsSaved={(updated) => onProfileUpdated?.(updated)}
      />
    </div>
  );
}
