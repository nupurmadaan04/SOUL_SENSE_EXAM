// Export all dashboard components
// Note: Heavy chart components using recharts are dynamically imported from @/lib/dynamic-imports
// to prevent bloating the initial bundle. Use: import { DashboardCharts } from '@/lib/dynamic-imports';

export * from './bento-grid';
export * from './stats-card';
export * from './leaderboard';
export * from './heatmap';
export * from './skeleton-loader';
export * from './reviewer-metrics';
export * from './contributor-details-modal';

// Chart components - these use recharts and are dynamically imported
// Export for direct use in dashboard ONLY
export * from './charts/activity-area-chart';
export * from './charts/contribution-mix';

export * from './pulse-feed';
export * from './good-first-issues';
export * from './project-roadmap';
export * from './welcome-card';
export * from './quick-actions';
export * from './mood-widget';
export * from './recent-activity';
export * from './insight-card';
export * from './section-wrapper';
export * from './PersonalizedAssessmentHub';

// ⚠️ DashboardCharts is NOT exported here to avoid eager loading recharts
// Use dynamic import instead:
//   import { DashboardCharts } from '@/lib/dynamic-imports';

