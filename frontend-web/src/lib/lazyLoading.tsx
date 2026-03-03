/**
 * Lazy loading configuration for Next.js components.
 * 
 * Implements:
 * - Dynamic imports for heavy components
 * - Code splitting by route
 * - Prefetching strategies
 */

import dynamic from 'next/dynamic';

// Lazy load heavy components
export const LazyDashboard = dynamic(() => import('@/components/dashboard/Dashboard'), {
  loading: () => <div className="animate-pulse">Loading dashboard...</div>,
  ssr: false,
});

export const LazyJournalEditor = dynamic(() => import('@/components/journal/JournalEditor'), {
  loading: () => <div className="animate-pulse">Loading editor...</div>,
  ssr: false,
});

export const LazyAnalytics = dynamic(() => import('@/components/dashboard/Analytics'), {
  loading: () => <div className="animate-pulse">Loading analytics...</div>,
  ssr: false,
});

export const LazyProfileSettings = dynamic(() => import('@/components/profile/ProfileSettings'), {
  loading: () => <div className="animate-pulse">Loading settings...</div>,
  ssr: false,
});

// Lazy load chart libraries
export const LazyCharts = dynamic(() => import('@/components/results/Charts'), {
  loading: () => <div className="animate-pulse">Loading charts...</div>,
  ssr: false,
});

/**
 * Prefetch configuration
 */
export const prefetchConfig = {
  onHover: { delay: 100 },
  onViewport: { rootMargin: '50px' },
};
