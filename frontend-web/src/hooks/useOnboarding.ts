'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSettings } from './useSettings';

export function useOnboarding() {
    const { settings, updateSettings, isLoading } = useSettings();
    const [showTutorial, setShowTutorial] = useState(false);

    useEffect(() => {
        if (!isLoading && settings && settings.onboarding_completed === false) {
            setShowTutorial(true);
        }
    }, [isLoading, settings]);

    const completeOnboarding = useCallback(async () => {
        try {
            await updateSettings({ onboarding_completed: true });
            setShowTutorial(false);
        } catch (error) {
            console.error('Failed to complete onboarding:', error);
            // Fallback: hide it anyway to not annoy the user
            setShowTutorial(false);
        }
    }, [updateSettings]);

    const skipOnboarding = useCallback(async () => {
        // For now, skip also marks as completed to avoid showing on next reload
        // In a more complex flow, skip might just hide it for the session
        await completeOnboarding();
    }, [completeOnboarding]);

    const restartTutorial = useCallback(() => {
        setShowTutorial(true);
    }, []);

    return {
        showTutorial,
        setShowTutorial,
        completeOnboarding,
        skipOnboarding,
        restartTutorial,
        isLoading: isLoading || settings === null,
    };
import { useState, useCallback, useEffect } from 'react';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { profileApi, OnboardingData } from '@/lib/api/profile';
import { useSearchParams, useRouter } from 'next/navigation';

export type OnboardingStep = 1 | 2 | 3;

export interface OnboardingState {
  /** Step 1: Welcome & Vision */
  primary_goal: string;
  focus_areas: string[];
  
  /** Step 2: Current Lifestyle */
  sleep_hours: number;
  exercise_freq: string;
  dietary_patterns: string;
  
  /** Step 3: Support System */
  has_therapist: boolean;
  support_network_size: number;
  primary_support_type: string;
}

const defaultState: OnboardingState = {
  primary_goal: '',
  focus_areas: [],
  sleep_hours: 7,
  exercise_freq: '',
  dietary_patterns: '',
  has_therapist: false,
  support_network_size: 3,
  primary_support_type: '',
};

export interface UseOnboardingReturn {
  // Status
  isLoading: boolean;
  isCheckingStatus: boolean;
  onboardingCompleted: boolean;
  error: string | null;
  
  // Step management
  currentStep: OnboardingStep;
  totalSteps: number;
  progress: number;
  goToStep: (step: OnboardingStep) => void;
  nextStep: () => void;
  prevStep: () => void;
  
  // Form state
  formData: OnboardingState;
  updateField: <K extends keyof OnboardingState>(field: K, value: OnboardingState[K]) => void;
  updateFields: (fields: Partial<OnboardingState>) => void;
  
  // Submission
  isSubmitting: boolean;
  submitOnboarding: () => Promise<void>;
  
  // Reset
  reset: () => void;
}

export function useOnboarding(): UseOnboardingReturn {
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Get step from URL query param (?step=2) for state persistence
  const stepParam = searchParams.get('step');
  const initialStep = (parseInt(stepParam || '1', 10) as OnboardingStep) || 1;
  
  // Local state
  const [currentStep, setCurrentStep] = useState<OnboardingStep>(initialStep);
  const [formData, setFormData] = useState<OnboardingState>(defaultState);
  const [error, setError] = useState<string | null>(null);
  
  // Query for onboarding status
  const {
    data: statusData,
    isLoading: isCheckingStatus,
  } = useQuery({
    queryKey: ['onboarding', 'status'],
    queryFn: () => profileApi.getOnboardingStatus(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
  
  const onboardingCompleted = statusData?.onboarding_completed || false;
  
  // Mutation for completing onboarding
  const {
    mutateAsync: completeOnboardingMutation,
    isPending: isSubmitting,
  } = useMutation({
    mutationFn: (data: OnboardingData) => profileApi.completeOnboarding(data),
    onSuccess: () => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['onboarding', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
  });
  
  // Sync step with URL query param
  useEffect(() => {
    const newStep = parseInt(searchParams.get('step') || '1', 10) as OnboardingStep;
    if (newStep >= 1 && newStep <= 3 && newStep !== currentStep) {
      setCurrentStep(newStep);
    }
  }, [searchParams, currentStep]);
  
  // Update URL when step changes
  const goToStep = useCallback((step: OnboardingStep) => {
    setCurrentStep(step);
    setError(null);
    
    // Update URL without full navigation
    const params = new URLSearchParams(searchParams.toString());
    params.set('step', step.toString());
    router.replace(`?${params.toString()}`, { scroll: false });
  }, [router, searchParams]);
  
  const nextStep = useCallback(() => {
    if (currentStep < 3) {
      goToStep((currentStep + 1) as OnboardingStep);
    }
  }, [currentStep, goToStep]);
  
  const prevStep = useCallback(() => {
    if (currentStep > 1) {
      goToStep((currentStep - 1) as OnboardingStep);
    }
  }, [currentStep, goToStep]);
  
  // Form state management
  const updateField = useCallback(<K extends keyof OnboardingState>(
    field: K,
    value: OnboardingState[K]
  ) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  }, []);
  
  const updateFields = useCallback((fields: Partial<OnboardingState>) => {
    setFormData(prev => ({ ...prev, ...fields }));
  }, []);
  
  // Submit onboarding data
  const submitOnboarding = useCallback(async () => {
    setError(null);
    
    try {
      const data: OnboardingData = {
        primary_goal: formData.primary_goal || undefined,
        focus_areas: formData.focus_areas.length > 0 ? formData.focus_areas : undefined,
        sleep_hours: formData.sleep_hours || undefined,
        exercise_freq: formData.exercise_freq || undefined,
        dietary_patterns: formData.dietary_patterns || undefined,
        has_therapist: formData.has_therapist,
        support_network_size: formData.support_network_size || undefined,
        primary_support_type: formData.primary_support_type || undefined,
      };
      
      await completeOnboardingMutation(data);
    } catch (err: any) {
      const errorMessage = err?.message || 'Failed to complete onboarding. Please try again.';
      setError(errorMessage);
      throw err;
    }
  }, [formData, completeOnboardingMutation]);
  
  // Reset form
  const reset = useCallback(() => {
    setFormData(defaultState);
    setCurrentStep(1);
    setError(null);
  }, []);
  
  // Calculate progress
  const progress = (currentStep / 3) * 100;
  
  return {
    isLoading: isCheckingStatus || isSubmitting,
    isCheckingStatus,
    onboardingCompleted,
    error,
    currentStep,
    totalSteps: 3,
    progress,
    goToStep,
    nextStep,
    prevStep,
    formData,
    updateField,
    updateFields,
    isSubmitting,
    submitOnboarding,
    reset,
  };
}
