'use client';

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useOnboardingGuard } from '@/hooks/useOnboardingGuard';
import { OnboardingModal } from '@/components/onboarding';
import { Sidebar, Header } from '@/components/app';
import { useOnboarding } from '@/hooks/useOnboarding';
import { OnboardingTutorial } from '@/components/onboarding/OnboardingTutorial';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  // Authentication checks are handled by Edge middleware; this hook is used only for UI state
  const { isAuthenticated, isLoading } = useAuth();
  const { showTutorial, completeOnboarding, skipOnboarding } = useOnboarding();
import { Loader } from '@/components/ui';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  // Authentication checks are handled by Edge middleware; this hook is used only for UI state
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  
  // Onboarding guard - intercepts new users
  const { needsOnboarding, isChecking, markComplete, skipForSession } = useOnboardingGuard();
  
  // Show loader while checking auth or onboarding status
  if (isAuthLoading || isChecking) {
    return (
      <div className="flex h-screen bg-background text-foreground">
        <Loader fullScreen text="Loading your experience..." />
      </div>
    );
  }

  return (
    <>
      {/* Onboarding Modal - intercepts new users */}
      <OnboardingModal
        isOpen={needsOnboarding}
        onComplete={markComplete}
        onSkip={skipForSession}
        preventClose={true}
      />
      
      {/* Main App Layout */}
      <div className="flex h-screen bg-background text-foreground relative">
        <Sidebar />

        {/* Main content area: flex-1 ensures it expands to fill all remaining space
            when the sidebar collapses (desktop 80px strip) or is removed from flow (mobile fixed positioning) */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <Header />
          <main className="flex-1 overflow-y-auto p-4 md:p-8">
            {children}
          </main>
        </div>
      </div>

      {showTutorial && (
        <OnboardingTutorial
          onComplete={completeOnboarding}
          onSkip={skipOnboarding}
        />
      )}
    </div>
    </>
  );
}
