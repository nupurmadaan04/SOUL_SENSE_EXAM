'use client';

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useOnboardingGuard } from '@/hooks/useOnboardingGuard';
import { OnboardingModal } from '@/components/onboarding';
import { Sidebar, Header } from '@/components/app';
import { useOnboarding } from '@/hooks/useOnboarding';
import { OnboardingTutorial } from '@/components/onboarding/OnboardingTutorial';
import { Loader } from '@/components/ui';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  // Authentication checks are handled by Edge middleware; this hook is used only for UI state
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const { showTutorial, completeOnboarding, skipOnboarding } = useOnboarding();
  
  // Onboarding guard - intercepts new users
  const { needsOnboarding, isChecking, markComplete, skipForSession } = useOnboardingGuard();
  
  // Show loader only on initial auth load when not yet authenticated
  if (isAuthLoading && !isAuthenticated) {
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

        {/* Main content area */}
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
    </>
  );
}
