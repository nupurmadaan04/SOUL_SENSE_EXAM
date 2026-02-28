'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from './useAuth';
import { toast } from '@/lib/toast';

/**
 * Session timeout configuration
 */
const INACTIVITY_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes in milliseconds
const WARNING_THRESHOLD_MS = 30 * 1000; // 30 seconds warning before timeout
const ACTIVITY_THROTTLE_MS = 1000; // Throttle activity tracking to once per second

interface UseSessionTimeoutOptions {
  enabled?: boolean;
  onTimeout?: () => void;
  onWarning?: (remainingSeconds: number) => void;
}

/**
 * Hook to manage session timeout based on user inactivity.
 * Automatically logs out the user after a period of inactivity.
 * 
 * Features:
 * - Tracks mouse, keyboard, and touch activity
 * - Shows warning before timeout
 * - Auto-logout when timeout is reached
 * - Resets timer on user activity
 * 
 * @example
 * ```tsx
 * function App() {
 *   useSessionTimeout({ enabled: true });
 *   return <div>...</div>;
 * }
 * ```
 */
export function useSessionTimeout(options: UseSessionTimeoutOptions = {}) {
  const { enabled = true, onTimeout, onWarning } = options;
  const { logout, isAuthenticated } = useAuth();
  const router = useRouter();
  
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const warningRef = useRef<NodeJS.Timeout | null>(null);
  const lastActivityRef = useRef<number>(Date.now());
  const lastMotionProcessRef = useRef<number>(0);
  const [showWarning, setShowWarning] = useState(false);
  const [remainingSeconds, setRemainingSeconds] = useState(0);

  /**
   * Perform logout due to inactivity
   */
  const handleTimeout = useCallback(() => {
    toast.error('Your session has expired due to inactivity. Please log in again.');
    
    // Clear all timeouts
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (warningRef.current) {
      clearTimeout(warningRef.current);
      warningRef.current = null;
    }
    
    // Call custom timeout handler if provided
    onTimeout?.();
    
    // Perform logout
    logout();
  }, [logout, onTimeout]);

  /**
   * Show warning before timeout
   */
  const handleWarning = useCallback(() => {
    const remaining = WARNING_THRESHOLD_MS / 1000;
    setRemainingSeconds(remaining);
    setShowWarning(true);
    
    onWarning?.(remaining);
    
    // Start countdown
    const countdownInterval = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(countdownInterval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    // Store interval to clear later
    warningRef.current = countdownInterval as unknown as NodeJS.Timeout;
  }, [onWarning]);

  /**
   * Reset the inactivity timer
   */
  const resetTimer = useCallback(() => {
    if (!enabled || !isAuthenticated) return;
    
    const now = Date.now();
    lastActivityRef.current = now;
    
    // Clear existing timeouts
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    if (warningRef.current) {
      clearTimeout(warningRef.current);
      setShowWarning(false);
    }
    
    // Set new timeout for warning
    const warningTime = INACTIVITY_TIMEOUT_MS - WARNING_THRESHOLD_MS;
    warningRef.current = setTimeout(handleWarning, warningTime);
    
    // Set new timeout for logout
    timeoutRef.current = setTimeout(handleTimeout, INACTIVITY_TIMEOUT_MS);
  }, [enabled, isAuthenticated, handleWarning, handleTimeout]);

  /**
   * Handle user activity
   */
  const handleActivity = useCallback(() => {
    const now = Date.now();
    
    // Throttle activity tracking
    if (now - lastMotionProcessRef.current < ACTIVITY_THROTTLE_MS) {
      return;
    }
    lastMotionProcessRef.current = now;
    
    // Reset the timer on activity
    resetTimer();
  }, [resetTimer]);

  /**
   * Handle mouse movement with throttling
   */
  const handleMouseMove = useCallback(() => {
    handleActivity();
  }, [handleActivity]);

  /**
   * Continue session - dismiss warning and reset timer
   */
  const continueSession = useCallback(() => {
    setShowWarning(false);
    resetTimer();
    toast.success('Session extended');
  }, [resetTimer]);

  // Set up activity listeners
  useEffect(() => {
    if (!enabled || !isAuthenticated) {
      // Clean up if disabled or not authenticated
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      if (warningRef.current) {
        clearTimeout(warningRef.current);
        warningRef.current = null;
      }
      return;
    }

    // Initialize timer
    resetTimer();

    // Add event listeners for user activity
    const events = [
      'mousedown',
      'mousemove',
      'keypress',
      'scroll',
      'touchstart',
      'click',
      'keydown',
      'wheel',
    ];

    events.forEach((event) => {
      window.addEventListener(event, handleActivity, { passive: true });
    });

    // Handle beforeunload to clean up
    const handleBeforeUnload = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (warningRef.current) {
        clearTimeout(warningRef.current);
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    // Cleanup
    return () => {
      events.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
      window.removeEventListener('beforeunload', handleBeforeUnload);
      
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (warningRef.current) {
        clearTimeout(warningRef.current);
      }
    };
  }, [enabled, isAuthenticated, resetTimer, handleActivity]);

  return {
    showWarning,
    remainingSeconds,
    continueSession,
    resetTimer,
    lastActivity: lastActivityRef.current,
  };
}

export default useSessionTimeout;
