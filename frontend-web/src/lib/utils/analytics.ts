/**
 * Analytics Utility with Standardized Event Names
 * All event names follow strict snake_case convention.
 * Event Schema Version: 1.0
 */

// Event name constants - must match shared/analytics/event_schema.json
export const ANALYTICS_EVENTS = {
  // Screen view events
  SCREEN_VIEW: 'screen_view',
  LOGIN_SCREEN_VIEW: 'login_screen_view',
  SIGNUP_SCREEN_VIEW: 'signup_screen_view',
  PROFILE_SCREEN_VIEW: 'profile_screen_view',
  SETTINGS_SCREEN_VIEW: 'settings_screen_view',

  // User interaction events
  BUTTON_CLICK: 'button_click',
  START_BUTTON_CLICK: 'start_button_click',
  LOGIN_BUTTON_CLICK: 'login_button_click',
  SIGNUP_BUTTON_CLICK: 'signup_button_click',
  LOGOUT_BUTTON_CLICK: 'logout_button_click',

  // Authentication events
  SIGNUP_START: 'signup_start',
  SIGNUP_SUCCESS: 'signup_success',
  SIGNUP_FAILURE: 'signup_failure',
  LOGIN_ATTEMPT: 'login_attempt',
  LOGIN_SUCCESS: 'login_success',
  LOGIN_FAILURE: 'login_failure',

  // Payment events
  PAYMENT_START: 'payment_start',
  PAYMENT_SUCCESS: 'payment_success',
  PAYMENT_FAILURE: 'payment_failure',

  // Feature usage events
  JOURNAL_ENTRY_CREATED: 'journal_entry_created',
  ASSESSMENT_STARTED: 'assessment_started',
  ASSESSMENT_COMPLETED: 'assessment_completed',
  REPORT_VIEWED: 'report_viewed',

  // System events
  APP_LAUNCH: 'app_launch',
  APP_BACKGROUND: 'app_background',
  APP_FOREGROUND: 'app_foreground',
  APP_CRASH: 'app_crash',
  DEVICE_ROTATION: 'device_rotation',

  // Session events
  SESSION_START: 'session_start',
  SESSION_END: 'session_end',

  // Engagement & behavior events
  SCROLL_DEPTH_25: 'scroll_depth_25',
  SCROLL_DEPTH_50: 'scroll_depth_50',
  SCROLL_DEPTH_75: 'scroll_depth_75',
  SCROLL_DEPTH_100: 'scroll_depth_100',

  // Screen time tracking events
  SCREEN_ENTER: 'screen_enter',
  SCREEN_EXIT: 'screen_exit',

  // Error events
  API_ERROR: 'api_error',
  NETWORK_ERROR: 'network_error',
  VALIDATION_ERROR: 'validation_error',
  VALIDATION_FAILED: 'validation_failed',
} as const;

type AnalyticsEventName = typeof ANALYTICS_EVENTS[keyof typeof ANALYTICS_EVENTS];

interface AnalyticsEvent {
  event_name: AnalyticsEventName;
  timestamp: string;
  user_id?: string;
  session_id: string;
  platform: 'web' | 'ios' | 'android' | 'desktop';
  app_version: string;
  device_info?: {
    model?: string;
    os_version?: string;
    screen_resolution?: string;
  };
  event_properties?: Record<string, any>;
}

interface AnalyticsConfig {
  enabled: boolean;
  provider?: 'vercel' | 'ga4' | 'mixpanel' | 'console';
}

// Schema validation function
function validateEventSchema(event: AnalyticsEvent): boolean {
  // Basic validation - in production, use a proper JSON schema validator
  const requiredFields = ['event_name', 'timestamp', 'session_id', 'platform', 'app_version'];
  for (const field of requiredFields) {
    if (!(field in event)) {
      console.error(`[Analytics] Missing required field: ${field}`);
      return false;
    }
  }

  // Validate event name format (snake_case)
  if (!/^[a-z][a-z0-9_]*$/.test(event.event_name)) {
    console.error(`[Analytics] Invalid event name format: ${event.event_name}`);
    return false;
  }

  return true;
}

class AnalyticsManager {
  private config: AnalyticsConfig = { enabled: false };
  private currentUserId: string | null = null;
  private currentSessionId: string;
  private sessionStartTime: number = 0;
  private isSessionActive: boolean = false;
  private guestUserId: string | null = null;

  // Screen time tracking
  private currentScreen: string | null = null;
  private screenEnterTime: number = 0;
  private screenEnterTimestamp: string = '';

  constructor() {
    this.currentSessionId = this.generateSessionId();
    this.initializeUserIdentity();
    this.setupSessionTracking();
    this.setupScrollDepthTracking();
    this.setupScreenTimeTracking();
    this.setupNetworkInterceptor();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateGuestId(): string {
    return `guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private initializeUserIdentity() {
    // Check if we are in a browser environment before accessing localStorage
    if (typeof window !== 'undefined' && typeof localStorage !== 'undefined') {
      const storedGuestId = localStorage.getItem('analytics_guest_id');
      if (storedGuestId) {
        this.guestUserId = storedGuestId;
      } else {
        // Generate new guest ID for first-time users
        this.guestUserId = this.generateGuestId();
        localStorage.setItem('analytics_guest_id', this.guestUserId);
      }
      // Initially use guest ID as user ID
      this.currentUserId = this.guestUserId;
    } else {
      // Fallback for non-browser environments
      this.guestUserId = this.generateGuestId();
      this.currentUserId = this.guestUserId;
    }
  }

  private setupSessionTracking() {
    // Track app visibility changes for session management
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
          this.endSession();
        } else {
          this.startSession();
        }
      });

      // Handle page unload (tab close, navigation)
      window.addEventListener('beforeunload', () => {
        this.endSession();
      });

      // Handle page load
      window.addEventListener('load', () => {
        this.startSession();
      });
    }
  }

  private setupScrollDepthTracking() {
    // Track scroll depth on pages with scrollable content
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
      // Use a throttled scroll handler to avoid excessive tracking
      let scrollTimeout: NodeJS.Timeout;
      const scrollThresholds = [25, 50, 75, 100];
      const reachedThresholds = new Set<number>();

      const handleScroll = () => {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
          const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
          const windowHeight = window.innerHeight;
          const documentHeight = Math.max(
            document.body.scrollHeight,
            document.body.offsetHeight,
            document.documentElement.clientHeight,
            document.documentElement.scrollHeight,
            document.documentElement.offsetHeight
          );

          const scrollPercentage = Math.round(((scrollTop + windowHeight) / documentHeight) * 100);

          // Check each threshold
          for (const threshold of scrollThresholds) {
            if (scrollPercentage >= threshold && !reachedThresholds.has(threshold)) {
              reachedThresholds.add(threshold);
              this.trackScrollDepth(threshold);
            }
          }
        }, 100); // Throttle to 100ms
      };

      // Add scroll event listener
      window.addEventListener('scroll', handleScroll, { passive: true });

      // Reset thresholds on page navigation (SPA routing)
      // This is a simplified approach - in a real SPA, you'd listen to route changes
      let currentPath = window.location.pathname;
      const checkPathChange = () => {
        if (window.location.pathname !== currentPath) {
          currentPath = window.location.pathname;
          reachedThresholds.clear();
        }
      };

      // Check for path changes periodically (for SPA navigation)
      setInterval(checkPathChange, 1000);
    }
  }

  private setupScreenTimeTracking() {
    // Handle screen exits on page visibility changes and before unload
    if (typeof document !== 'undefined') {
      // Handle app background/foreground
      document.addEventListener('visibilitychange', () => {
        if (document.hidden && this.currentScreen) {
          // App going to background - exit current screen
          this.exitScreen('background');
        } else if (!document.hidden && this.currentScreen) {
          // App coming to foreground - re-enter current screen
          this.enterScreen(this.currentScreen);
        }
      });

      // Handle page unload (tab close, navigation)
      window.addEventListener('beforeunload', () => {
        if (this.currentScreen) {
          this.exitScreen('force_close');
        }
      });

      // Handle browser navigation (back/forward buttons, direct URL changes)
      window.addEventListener('popstate', () => {
        if (this.currentScreen) {
          this.exitScreen('navigation');
        }
      });
    }
  }

  private setupNetworkInterceptor() {
    // Intercept fetch requests for API error tracking
    if (typeof window !== 'undefined' && typeof fetch !== 'undefined') {
      const originalFetch = window.fetch;

      window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
        const startTime = Date.now();
        let retryCount = 0;

        // Extract endpoint URL
        const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;

        try {
          const response = await originalFetch(input, init);
          const latency = Date.now() - startTime;

          // Track API errors (4xx, 5xx status codes)
          if (!response.ok) {
            let errorMessage = `HTTP ${response.status}`;
            try {
              const errorData = await response.clone().json();
              if (errorData.message) {
                errorMessage = errorData.message;
              }
            } catch {
              // If we can't parse the error response, use the status text
              if (response.statusText) {
                errorMessage = response.statusText;
              }
            }

            this.trackApiError(url, response.status, errorMessage, latency, retryCount);
          }

          return response;
        } catch (error) {
          const latency = Date.now() - startTime;
          const errorMessage = error instanceof Error ? error.message : 'Network request failed';

          // Track network/timeout errors
          this.trackApiError(url, 0, errorMessage, latency, retryCount);

          throw error;
        }
      };
    }
  }

  private startSession() {
    if (this.isSessionActive) return;

    this.sessionStartTime = Date.now();
    this.isSessionActive = true;

    this.trackEvent({
      event_name: ANALYTICS_EVENTS.SESSION_START,
      timestamp: new Date().toISOString(),
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: {}
    });
  }

  private endSession() {
    if (!this.isSessionActive) return;

    const sessionDuration = Date.now() - this.sessionStartTime;
    this.isSessionActive = false;

    this.trackEvent({
      event_name: ANALYTICS_EVENTS.SESSION_END,
      timestamp: new Date().toISOString(),
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: {
        session_duration_ms: sessionDuration,
        session_duration_seconds: Math.round(sessionDuration / 1000)
      }
    });

    // Generate new session ID for next session
    this.currentSessionId = this.generateSessionId();
  }

  configure(config: AnalyticsConfig) {
    this.config = { ...this.config, ...config };
  }

  // User identity management
  setUserId(userId: string) {
    // Clear guest ID when user logs in
    if (this.currentUserId === this.guestUserId) {
      if (typeof window !== 'undefined' && typeof localStorage !== 'undefined') {
        localStorage.removeItem('analytics_guest_id');
      }
      this.guestUserId = null;
    }
    this.currentUserId = userId;
  }

  clearUserId() {
    this.currentUserId = this.guestUserId;
  }

  getCurrentUserId(): string | null {
    return this.currentUserId;
  }

  getGuestUserId(): string | null {
    return this.guestUserId;
  }

  trackPageView(url: string) {
    if (!this.config.enabled) return;

    // Track screen enter for time tracking
    this.enterScreen(url);

    const event: AnalyticsEvent = {
      event_name: ANALYTICS_EVENTS.SCREEN_VIEW,
      timestamp: new Date().toISOString(),
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: { screen_name: url }
    };

    this.trackEvent(event);
  }

  trackEvent(event: AnalyticsEvent) {
    if (!this.config.enabled) return;

    // Ensure user_id is set if not provided
    if (!event.user_id && this.currentUserId) {
      event.user_id = this.currentUserId;
    }

    if (!validateEventSchema(event)) {
      console.error('[Analytics] Event validation failed, not tracking');
      return;
    }

    // Send to configured provider
    switch (this.config.provider) {
      case 'vercel':
        // va.track(event.event_name, event);
        break;
      case 'ga4':
        // gtag('event', event.event_name, event);
        break;
      case 'mixpanel':
        // mixpanel.track(event.event_name, event);
        break;
      default:
        console.log(`[Analytics] Event: ${event.event_name}`, event);
    }
  }

  private trackScrollDepth(percentage: number) {
    const eventName = percentage === 25 ? ANALYTICS_EVENTS.SCROLL_DEPTH_25 :
                     percentage === 50 ? ANALYTICS_EVENTS.SCROLL_DEPTH_50 :
                     percentage === 75 ? ANALYTICS_EVENTS.SCROLL_DEPTH_75 :
                     ANALYTICS_EVENTS.SCROLL_DEPTH_100;

    this.trackEvent({
      event_name: eventName,
      timestamp: new Date().toISOString(),
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: {
        scroll_percentage: percentage,
        page_url: typeof window !== 'undefined' ? window.location.href : undefined
      }
    });
  }

  private enterScreen(screenName: string) {
    // Exit current screen if any
    if (this.currentScreen) {
      this.exitScreen('navigation');
    }

    // Enter new screen
    this.currentScreen = screenName;
    this.screenEnterTime = Date.now();
    this.screenEnterTimestamp = new Date().toISOString();

    this.trackEvent({
      event_name: ANALYTICS_EVENTS.SCREEN_ENTER,
      timestamp: this.screenEnterTimestamp,
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: {
        screen_name: screenName,
        enter_time: this.screenEnterTimestamp
      }
    });
  }

  private exitScreen(exitReason: 'navigation' | 'background' | 'force_close' | 'app_close') {
    if (!this.currentScreen || this.screenEnterTime === 0) return;

    const exitTime = Date.now();
    const exitTimestamp = new Date().toISOString();
    const durationMs = exitTime - this.screenEnterTime;
    const durationSeconds = Math.round(durationMs / 1000);

    this.trackEvent({
      event_name: ANALYTICS_EVENTS.SCREEN_EXIT,
      timestamp: exitTimestamp,
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: {
        screen_name: this.currentScreen,
        enter_time: this.screenEnterTimestamp,
        exit_time: exitTimestamp,
        duration_ms: durationMs,
        duration_seconds: durationSeconds,
        exit_reason: exitReason
      }
    });

    // Reset screen tracking
    this.currentScreen = null;
    this.screenEnterTime = 0;
    this.screenEnterTimestamp = '';
  }

  // Convenience methods for common events
  trackButtonClick(buttonName: string, elementType: 'button' | 'link' | 'menu_item' = 'button') {
    this.trackEvent({
      event_name: ANALYTICS_EVENTS.BUTTON_CLICK,
      timestamp: new Date().toISOString(),
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: { button_name: buttonName, element_type: elementType }
    });
  }

  trackSignupStart(method: 'email' | 'google' | 'apple' | 'facebook', referralCode?: string) {
    this.trackEvent({
      event_name: ANALYTICS_EVENTS.SIGNUP_START,
      timestamp: new Date().toISOString(),
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: { method, referral_code: referralCode }
    });
  }

  trackLoginSuccess() {
    this.trackEvent({
      event_name: ANALYTICS_EVENTS.LOGIN_SUCCESS,
      timestamp: new Date().toISOString(),
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: {}
    });
  }

  trackLogout() {
    this.trackEvent({
      event_name: ANALYTICS_EVENTS.LOGOUT_BUTTON_CLICK,
      timestamp: new Date().toISOString(),
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: {}
    });
  }

  trackError(errorType: 'network' | 'api' | 'validation', errorCode?: string, errorMessage?: string) {
    const eventName = errorType === 'network' ? ANALYTICS_EVENTS.NETWORK_ERROR :
                     errorType === 'api' ? ANALYTICS_EVENTS.API_ERROR :
                     ANALYTICS_EVENTS.VALIDATION_ERROR;

    this.trackEvent({
      event_name: eventName,
      timestamp: new Date().toISOString(),
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: { error_code: errorCode, error_message: errorMessage }
    });
  }

  trackApiError(endpoint: string, responseCode: number, errorMessage: string, latency: number, retryCount: number = 0) {
    this.trackEvent({
      event_name: ANALYTICS_EVENTS.API_ERROR,
      timestamp: new Date().toISOString(),
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: {
        endpoint,
        response_code: responseCode,
        error_message: errorMessage,
        latency,
        retry_count: retryCount
      }
    });
  }

  trackValidationFailure(fieldName: string, reason: string) {
    this.trackEvent({
      event_name: ANALYTICS_EVENTS.VALIDATION_FAILED,
      timestamp: new Date().toISOString(),
      user_id: this.currentUserId || undefined,
      session_id: this.currentSessionId,
      platform: 'web',
      app_version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      event_properties: {
        field_name: fieldName,
        reason
      }
    });
  }

  // Manual session control (for special cases)
  forceEndSession() {
    this.endSession();
  }

  forceStartSession() {
    this.startSession();
  }
}

export const analytics = new AnalyticsManager();
