'use client';

import React from 'react';
import { useSessionTimeout } from '@/hooks/useSessionTimeout';
import { Button } from '@/components/ui';
import { AlertCircle, Clock } from 'lucide-react';

/**
 * Session Timeout Warning Modal
 * 
 * Displays a warning dialog when the user's session is about to expire
 * due to inactivity. Allows the user to extend their session.
 */
export function SessionTimeoutWarning() {
  const { showWarning, remainingSeconds, continueSession } = useSessionTimeout({
    enabled: true,
  });

  if (!showWarning) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="flex items-center gap-3 text-amber-500">
          <AlertCircle className="h-8 w-8" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Session Timeout Warning
          </h2>
        </div>

        <div className="mt-4 space-y-4">
          <p className="text-gray-600 dark:text-gray-300">
            You have been inactive for a while. For security reasons, your session
            will expire soon.
          </p>

          <div className="flex items-center justify-center gap-2 rounded-lg bg-amber-50 p-4 dark:bg-amber-900/20">
            <Clock className="h-5 w-5 text-amber-500" />
            <span className="text-lg font-semibold text-amber-700 dark:text-amber-400">
              {remainingSeconds} second{remainingSeconds !== 1 ? 's' : ''} remaining
            </span>
          </div>

          <p className="text-sm text-gray-500 dark:text-gray-400">
            Click the button below to stay logged in and continue your session.
          </p>
        </div>

        <div className="mt-6 flex justify-center">
          <Button
            onClick={continueSession}
            size="lg"
            className="min-w-[200px] bg-primary hover:bg-primary/90"
          >
            Continue Session
          </Button>
        </div>
      </div>
    </div>
  );
}

export default SessionTimeoutWarning;
