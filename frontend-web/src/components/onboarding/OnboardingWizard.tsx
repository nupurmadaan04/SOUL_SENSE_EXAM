'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useOnboarding, OnboardingStep } from '@/hooks/useOnboarding';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { 
  Sparkles, 
  Heart, 
  Users, 
  ChevronRight, 
  ChevronLeft,
  Check,
  Moon,
  Dumbbell,
  Apple,
  Stethoscope,
  Target,
  Leaf
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ============================================================================
// Step 1: Welcome & Vision
// ============================================================================

const FOCUS_AREA_OPTIONS = [
  { id: 'career', label: 'Career Growth', icon: Target },
  { id: 'relationships', label: 'Relationships', icon: Heart },
  { id: 'health', label: 'Physical Health', icon: Leaf },
  { id: 'mental_health', label: 'Mental Health', icon: Sparkles },
  { id: 'finance', label: 'Financial Wellness', icon: Target },
  { id: 'personal_growth', label: 'Personal Growth', icon: Sparkles },
];

function WelcomeVisionStep({ 
  formData, 
  updateField,
  updateFields,
}: { 
  formData: ReturnType<typeof useOnboarding>['formData'];
  updateField: ReturnType<typeof useOnboarding>['updateField'];
  updateFields: ReturnType<typeof useOnboarding>['updateFields'];
}) {
  const toggleFocusArea = (areaId: string) => {
    const current = formData.focus_areas;
    const updated = current.includes(areaId)
      ? current.filter(id => id !== areaId)
      : [...current, areaId];
    updateField('focus_areas', updated);
  };

  return (
    <div className="space-y-8">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-2">
          <Sparkles className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-2xl font-bold text-foreground">Welcome to SoulSense</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          Let&apos;s personalize your experience. What brings you here today?
        </p>
      </div>

      {/* Primary Goal */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-foreground">
          What&apos;s your primary goal?
        </label>
        <textarea
          value={formData.primary_goal}
          onChange={(e) => updateField('primary_goal', e.target.value)}
          placeholder="e.g., I want to better understand my emotions and improve my relationships..."
          className="w-full min-h-[100px] px-4 py-3 rounded-lg border border-input bg-background/50 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
          maxLength={500}
        />
        <div className="text-xs text-muted-foreground text-right">
          {formData.primary_goal.length}/500
        </div>
      </div>

      {/* Focus Areas */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-foreground">
          What areas would you like to focus on? (Select all that apply)
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {FOCUS_AREA_OPTIONS.map((area) => {
            const Icon = area.icon;
            const isSelected = formData.focus_areas.includes(area.id);
            return (
              <button
                key={area.id}
                onClick={() => toggleFocusArea(area.id)}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200',
                  isSelected
                    ? 'border-primary bg-primary/5 text-primary'
                    : 'border-border/50 bg-background/50 hover:border-primary/30 hover:bg-muted/30'
                )}
              >
                <Icon className={cn('w-6 h-6', isSelected ? 'text-primary' : 'text-muted-foreground')} />
                <span className="text-sm font-medium text-center">{area.label}</span>
                {isSelected && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute top-2 right-2"
                  >
                    <Check className="w-4 h-4 text-primary" />
                  </motion.div>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Step 2: Current Lifestyle
// ============================================================================

const EXERCISE_OPTIONS = [
  { value: 'daily', label: 'Daily', description: 'Every day' },
  { value: 'few_times_week', label: 'Few times a week', description: '3-4 times per week' },
  { value: 'once_week', label: 'Once a week', description: 'About once per week' },
  { value: 'rarely', label: 'Rarely', description: 'A few times a month' },
  { value: 'never', label: 'Never', description: 'I don\'t exercise' },
];

const DIETARY_OPTIONS = [
  { value: 'balanced', label: 'Balanced', description: 'A mix of all food groups' },
  { value: 'vegetarian', label: 'Vegetarian', description: 'No meat, may include dairy/eggs' },
  { value: 'vegan', label: 'Vegan', description: 'Plant-based, no animal products' },
  { value: 'keto', label: 'Keto/Low-carb', description: 'High fat, low carbohydrate' },
  { value: 'paleo', label: 'Paleo', description: 'Whole foods, no processed items' },
  { value: 'other', label: 'Other', description: 'Something else' },
];

function LifestyleStep({ 
  formData, 
  updateField,
}: { 
  formData: ReturnType<typeof useOnboarding>['formData'];
  updateField: ReturnType<typeof useOnboarding>['updateField'];
}) {
  return (
    <div className="space-y-8">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-2">
          <Leaf className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-2xl font-bold text-foreground">Your Lifestyle</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          Help us understand your daily habits to provide better insights.
        </p>
      </div>

      {/* Sleep Hours */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Moon className="w-5 h-5 text-primary" />
          <label className="text-sm font-medium text-foreground">
            How many hours do you sleep per night?
          </label>
        </div>
        <div className="px-2">
          <div className="flex justify-between text-xs text-muted-foreground mb-2">
            <span>4h</span>
            <span className="text-primary font-medium">{formData.sleep_hours}h</span>
            <span>12h</span>
          </div>
          <input
            type="range"
            min="4"
            max="12"
            step="0.5"
            value={formData.sleep_hours}
            onChange={(e) => updateField('sleep_hours', parseFloat(e.target.value))}
            className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
          />
        </div>
      </div>

      {/* Exercise Frequency */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Dumbbell className="w-5 h-5 text-primary" />
          <label className="text-sm font-medium text-foreground">
            How often do you exercise?
          </label>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {EXERCISE_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => updateField('exercise_freq', option.value)}
              className={cn(
                'p-4 rounded-xl border-2 text-left transition-all duration-200',
                formData.exercise_freq === option.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border/50 bg-background/50 hover:border-primary/30'
              )}
            >
              <div className="font-medium text-foreground">{option.label}</div>
              <div className="text-xs text-muted-foreground">{option.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Dietary Patterns */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Apple className="w-5 h-5 text-primary" />
          <label className="text-sm font-medium text-foreground">
            How would you describe your diet?
          </label>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {DIETARY_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => updateField('dietary_patterns', option.value)}
              className={cn(
                'p-4 rounded-xl border-2 text-left transition-all duration-200',
                formData.dietary_patterns === option.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border/50 bg-background/50 hover:border-primary/30'
              )}
            >
              <div className="font-medium text-foreground text-sm">{option.label}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Step 3: Support System
// ============================================================================

const SUPPORT_TYPE_OPTIONS = [
  { value: 'family', label: 'Family', icon: Users },
  { value: 'friends', label: 'Friends', icon: Users },
  { value: 'partner', label: 'Partner/Spouse', icon: Heart },
  { value: 'community', label: 'Community/Groups', icon: Users },
  { value: 'professional', label: 'Professional Support', icon: Stethoscope },
  { value: 'online', label: 'Online Communities', icon: Users },
];

function SupportSystemStep({ 
  formData, 
  updateField,
}: { 
  formData: ReturnType<typeof useOnboarding>['formData'];
  updateField: ReturnType<typeof useOnboarding>['updateField'];
}) {
  return (
    <div className="space-y-8">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-2">
          <Users className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-2xl font-bold text-foreground">Your Support System</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          Understanding your support network helps us tailor recommendations.
        </p>
      </div>

      {/* Therapist */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Stethoscope className="w-5 h-5 text-primary" />
          <label className="text-sm font-medium text-foreground">
            Are you currently working with a therapist or counselor?
          </label>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => updateField('has_therapist', true)}
            className={cn(
              'flex-1 py-3 px-4 rounded-xl border-2 font-medium transition-all duration-200',
              formData.has_therapist === true
                ? 'border-primary bg-primary/5 text-primary'
                : 'border-border/50 bg-background/50 hover:border-primary/30'
            )}
          >
            Yes
          </button>
          <button
            onClick={() => updateField('has_therapist', false)}
            className={cn(
              'flex-1 py-3 px-4 rounded-xl border-2 font-medium transition-all duration-200',
              formData.has_therapist === false
                ? 'border-primary bg-primary/5 text-primary'
                : 'border-border/50 bg-background/50 hover:border-primary/30'
            )}
          >
            No
          </button>
        </div>
      </div>

      {/* Support Network Size */}
      <div className="space-y-4">
        <label className="text-sm font-medium text-foreground">
          How many people do you consider part of your close support network?
        </label>
        <div className="px-2">
          <div className="flex justify-between text-xs text-muted-foreground mb-2">
            <span>0</span>
            <span className="text-primary font-medium text-base">{formData.support_network_size}</span>
            <span>20+</span>
          </div>
          <input
            type="range"
            min="0"
            max="20"
            step="1"
            value={formData.support_network_size}
            onChange={(e) => updateField('support_network_size', parseInt(e.target.value, 10))}
            className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
          />
          <div className="mt-2 text-xs text-muted-foreground text-center">
            {formData.support_network_size === 0 
              ? "I prefer to handle things on my own" 
              : formData.support_network_size < 3 
                ? "A small, close circle" 
                : formData.support_network_size < 8 
                  ? "A moderate support network" 
                  : "A large, diverse support network"}
          </div>
        </div>
      </div>

      {/* Primary Support Type */}
      <div className="space-y-4">
        <label className="text-sm font-medium text-foreground">
          Who do you turn to most for support?
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {SUPPORT_TYPE_OPTIONS.map((option) => {
            const Icon = option.icon;
            return (
              <button
                key={option.value}
                onClick={() => updateField('primary_support_type', option.value)}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200',
                  formData.primary_support_type === option.value
                    ? 'border-primary bg-primary/5'
                    : 'border-border/50 bg-background/50 hover:border-primary/30'
                )}
              >
                <Icon className={cn(
                  'w-5 h-5',
                  formData.primary_support_type === option.value ? 'text-primary' : 'text-muted-foreground'
                )} />
                <span className="text-sm font-medium text-center">{option.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Onboarding Wizard Component
// ============================================================================

export interface OnboardingWizardProps {
  onComplete?: () => void;
  onSkip?: () => void;
  className?: string;
}

export function OnboardingWizard({ onComplete, onSkip, className }: OnboardingWizardProps) {
  const {
    currentStep,
    totalSteps,
    progress,
    goToStep,
    nextStep,
    prevStep,
    formData,
    updateField,
    updateFields,
    isSubmitting,
    submitOnboarding,
    error,
  } = useOnboarding();

  const handleSubmit = async () => {
    try {
      await submitOnboarding();
      onComplete?.();
    } catch {
      onComplete?.();
    }
  };

  const stepTitles = ['Welcome & Vision', 'Current Lifestyle', 'Support System'];

  return (
    <div className={cn('w-full max-w-2xl mx-auto', className)}>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            {stepTitles.map((title, index) => {
              const stepNumber = (index + 1) as OnboardingStep;
              const isActive = currentStep === stepNumber;
              const isCompleted = currentStep > stepNumber;
              
              return (
                <React.Fragment key={stepNumber}>
                  <button
                    onClick={() => goToStep(stepNumber)}
                    className={cn(
                      'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200',
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : isCompleted
                          ? 'bg-primary/20 text-primary'
                          : 'bg-muted text-muted-foreground hover:bg-muted/80'
                    )}
                  >
                    <span className={cn(
                      'w-5 h-5 rounded-full flex items-center justify-center text-xs',
                      isActive
                        ? 'bg-primary-foreground text-primary'
                        : isCompleted
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted-foreground/20'
                    )}>
                      {isCompleted ? <Check className="w-3 h-3" /> : stepNumber}
                    </span>
                    <span className="hidden sm:inline">{title}</span>
                  </button>
                  {index < stepTitles.length - 1 && (
                    <div className={cn(
                      'w-8 h-0.5 transition-colors',
                      isCompleted ? 'bg-primary/50' : 'bg-muted'
                    )} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
        <Progress value={progress} showLabel={false} className="h-1.5" />
      </div>

      {/* Step Content */}
      <div className="bg-card/50 backdrop-blur-sm border rounded-2xl p-6 sm:p-8 shadow-sm">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
          >
            {currentStep === 1 && (
              <WelcomeVisionStep
                formData={formData}
                updateField={updateField}
                updateFields={updateFields}
              />
            )}
            {currentStep === 2 && (
              <LifestyleStep
                formData={formData}
                updateField={updateField}
              />
            )}
            {currentStep === 3 && (
              <SupportSystemStep
                formData={formData}
                updateField={updateField}
              />
            )}
          </motion.div>
        </AnimatePresence>

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 p-4 rounded-lg bg-destructive/10 text-destructive text-sm"
          >
            {error}
          </motion.div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="mt-8 flex items-center justify-between">
        <div>
          {currentStep === 1 && onSkip && (
            <Button variant="ghost" onClick={onSkip}>
              Skip for now
            </Button>
          )}
          {currentStep > 1 && (
            <Button variant="outline" onClick={prevStep} className="gap-2">
              <ChevronLeft className="w-4 h-4" />
              Back
            </Button>
          )}
        </div>

        <div className="flex items-center gap-3">
          {currentStep < totalSteps ? (
            <Button onClick={nextStep} className="gap-2">
              Continue
              <ChevronRight className="w-4 h-4" />
            </Button>
          ) : (
            <Button 
              onClick={handleSubmit} 
              disabled={isSubmitting}
              className="gap-2 min-w-[140px]"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Complete
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
