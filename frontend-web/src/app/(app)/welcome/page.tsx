'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { OnboardingWizard } from '@/components/onboarding';
import { useOnboarding } from '@/hooks/useOnboarding';
import { motion } from 'framer-motion';

export default function WelcomePage() {
  const router = useRouter();
  const { onboardingCompleted, submitOnboarding } = useOnboarding();
  
  // If onboarding is already complete, redirect to dashboard
  useEffect(() => {
    if (onboardingCompleted) {
      router.push('/dashboard');
    }
  }, [onboardingCompleted, router]);
  
  const handleComplete = () => {
    router.push('/dashboard');
  };
  
  const handleSkip = () => {
    router.push('/dashboard');
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      {/* Header */}
      <header className="border-b bg-background/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold">S</span>
            </div>
            <span className="font-semibold text-foreground">SoulSense</span>
          </div>
          <button
            onClick={handleSkip}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Skip for now
          </button>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="py-12 px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-foreground mb-4">
              Welcome to SoulSense
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Let&apos;s take a few minutes to personalize your experience. 
              This helps us provide insights and recommendations tailored specifically to you.
            </p>
          </div>
          
          <OnboardingWizard 
            onComplete={handleComplete}
            onSkip={handleSkip}
            className="max-w-2xl mx-auto"
          />
        </motion.div>
      </main>
      
      {/* Footer */}
      <footer className="border-t py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-muted-foreground">
          Your privacy is important to us. All your data is securely encrypted and never shared.
        </div>
      </footer>
    </div>
  );
}
