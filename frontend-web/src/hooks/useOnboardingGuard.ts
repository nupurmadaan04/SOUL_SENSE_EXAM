'use client';

import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';

export interface UseOnboardingGuardReturn {
  /** Whether the user needs to complete onboarding */
  needsOnboarding: boolean;
  /** Whether we're still checking the onboarding status */
  isChecking: boolean;
  /** Function to mark onboarding as complete locally */
  markComplete: () => void;
  /** Function to skip onboarding (for this session only) */
  skipForSession: () => void;
}

export function useOnboardingGuard(): UseOnboardingGuardReturn {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [skipped, setSkipped] = useState(false);
  const [locallyCompleted, setLocallyCompleted] = useState(false);

  // Trigger welcome modal immediately once after login or signup session
  const shouldShowWelcome =
    typeof window !== 'undefined' &&
    (sessionStorage.getItem('soulsense_welcome_session') === 'true' ||
      sessionStorage.getItem('soulsense_just_signed_up') === 'true');

  const needsOnboarding = shouldShowWelcome && !skipped && !locallyCompleted;
  const isChecking = false;

  // Mark onboarding as complete locally
  const markComplete = () => {
    setLocallyCompleted(true);
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('soulsense_welcome_session');
      sessionStorage.removeItem('soulsense_just_signed_up');
      localStorage.setItem('soulsense_onboarding_wizard_done', 'true');
    }
    queryClient.setQueryData(['onboarding', 'status'], { onboarding_completed: true });
    queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    queryClient.invalidateQueries({ queryKey: ['profile'] });
    router.push('/dashboard');
  };

  // Skip onboarding for this session
  const skipForSession = () => {
    setSkipped(true);
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('soulsense_welcome_session');
      sessionStorage.removeItem('soulsense_just_signed_up');
    }
    router.push('/dashboard');
  };

  return {
    needsOnboarding,
    isChecking,
    markComplete,
    skipForSession,
  };
}
