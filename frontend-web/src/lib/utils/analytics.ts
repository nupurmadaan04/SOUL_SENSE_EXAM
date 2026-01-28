/**
 * Mock Analytics Utility
 * Used for tracking page views and user interactions.
 * This can be easily replaced with a real provider (e.g., Vercel Analytics, GA4)
 */

type AnalyticsEvent = {
  category: string;
  action: string;
  label?: string;
  value?: number;
};

export const analytics = {
  trackPageView: (url: string) => {
    console.log(`[Analytics] Page View: ${url}`);
    // Future integration: va.track('page_view', { url });
  },

  trackEvent: (event: AnalyticsEvent) => {
    console.log(
      `[Analytics] Event: ${event.category} - ${event.action}`,
      event.label ? `(${event.label})` : ''
    );
    // Future integration: va.track(event.action, event);
  },
};
