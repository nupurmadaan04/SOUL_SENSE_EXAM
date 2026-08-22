'use client';

import { useEffect } from 'react';
import { register } from '@/lib/offline';

export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
      try {
        register();
      } catch (err) {
        console.warn('Service worker registration skipped:', err);
      }
    }
  }, []);

  return null;
}
