import { ApiError } from './errors';
import { sanitizeError, logError, shouldLogout, isRetryableError } from '../utils/errorHandler';
import { retryRequest } from '../utils/requestUtils';
import { getSession, saveSession, isTokenExpired, isSessionTimedOut, updateLastActivity } from '../utils/sessionStorage';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

// State variables for token refresh locking mechanism
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: any) => void;
}> = [];

// Process the queue of failed requests
const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

interface RequestOptions extends RequestInit {
  timeout?: number;
  skipAuth?: boolean; // For public endpoints like login
  retry?: boolean; // Enable retry for this request
  maxRetries?: number;
  responseType?: 'json' | 'blob';
  _isRetry?: boolean; // Internal flag for auth retry
  _token?: string; // Override token for retry
}

/**
 * Get authentication token from storage
 * NOTE: This uses session storage. Production should use httpOnly cookies.
 * See implementation_plan.md for migration guide.
 */
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  const session = getSession();
  const token = session?.token || null;

  // If token exists but is expired, return null to force the refresh logic in apiClient
  if (token && isTokenExpired(token)) {
    return null;
  }

  return token;
}

/**
 * Handle authentication failure
 */
function handleAuthFailure(): void {
  if (typeof window === 'undefined') return;

  // Dispatch custom event to let useAuth handle the cleanup
  window.dispatchEvent(new CustomEvent('auth-failure'));
}

/**
 * Check if session has timed out due to inactivity
 * Issue #999: Session timeout handling
 */
function checkSessionTimeout(): boolean {
  if (typeof window === 'undefined') return false;
  
  if (isSessionTimedOut()) {
    console.warn('Session timed out due to inactivity');
    handleAuthFailure();
    return true;
  }
  
  // Update last activity on API call
  updateLastActivity();
  return false;
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const {
    timeout = 30000,
    skipAuth = false,
    retry = false,
    maxRetries = 3,
    responseType = 'json',
    ...fetchOptions
  } = options;

  // Issue #999: Check for session timeout on authenticated requests
  if (!skipAuth && checkSessionTimeout()) {
    throw new ApiError(401, {
      message: 'Session expired due to inactivity. Please log in again.',
      code: 'SESSION_TIMEOUT',
    });
  }

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  // Inject authentication token
  const token = options._token || (skipAuth ? null : getAuthToken());
  const headers = new Headers(fetchOptions.headers);

  if (!headers.has('Content-Type') && !(fetchOptions.body instanceof FormData) && responseType !== 'blob') {
    headers.set('Content-Type', 'application/json');
  }

  if (token && !skipAuth) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const makeRequest = async (): Promise<T> => {
    try {
      const response = await fetch(url, {
        cache: options.cache || (endpoint.includes('/captcha') ? 'no-store' : undefined),
        ...fetchOptions,
        headers,
        signal: controller.signal,
      });

      clearTimeout(id);

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch {
          errorData = { message: `HTTP Error ${response.status}: ${response.statusText}` };
        }

        const apiError = new ApiError(response.status, errorData);

        // Handle 401 - Unauthorized
        if (response.status === 401) {
          if (options._isRetry) {
            throw apiError;
          }

          // Do not attempt refresh for explicit auth endpoints (login, register) or if skipAuth is true
          if (endpoint.includes('/auth/login') || endpoint.includes('/auth/register') || skipAuth) {
            throw apiError;
          }

          if (isRefreshing) {
            // Queue the request
            return new Promise((resolve, reject) => {
              failedQueue.push({ resolve, reject });
            }).then((token) => {
              return apiClient(endpoint, { ...options, _isRetry: true, _token: token as string });
            });
          }

          // Start refreshing
          isRefreshing = true;

          try {
            // Internal refresh fetch to avoid circular dependency
            const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
              method: 'POST',
              // Include cookies for refresh token
              credentials: 'include',
            });

            if (refreshRes.ok) {
              const data = await refreshRes.json();

              // Update session
              const session = getSession();
              if (session) {
                session.token = data.access_token;
                if (data.refresh_token) {
                  // Cookie is HTTPOnly
                }
                // Persist update (keeping existing storage type)
                saveSession(session, !!localStorage.getItem('soul_sense_auth_session'));
              }

              processQueue(null, data.access_token);

              // Retry original request with new token
              return apiClient(endpoint, { ...options, _isRetry: true, _token: data.access_token });
            } else {
              throw new Error('Refresh failed');
            }
          } catch (err) {
            console.error('Token refresh failed:', err);
            processQueue(err, null);
            handleAuthFailure();
            throw apiError;
          } finally {
            isRefreshing = false;
          }
        }

        throw apiError;
      }

      // Handle empty response (204 No Content)
      if (response.status === 204) {
        return {} as T;
      }

      if (responseType === 'blob') {
        return (await response.blob()) as unknown as T;
      }

      return await response.json();
    } catch (error: any) {
      clearTimeout(id);

      if (error.name === 'AbortError') {
        throw new ApiError(408, {
          message: 'Request timed out. Please check your internet connection.',
          isNetworkError: true,
        });
      }

      if (error instanceof ApiError) {
        throw error;
      }

      // Likely a network error (DNS, Connection Refused, etc.)
      const detailedMessage = `Network Error: [URL: ${url}] | Message: ${error.message || 'Unknown error'}`;
      throw new ApiError(0, {
        message: detailedMessage,
        isNetworkError: true,
        originalError: error.message,
      });
    }
  };

  // Retry if enabled and error is retryable
  if (retry) {
    return retryRequest(makeRequest, maxRetries, 1000, isRetryableError);
  }

  return makeRequest();
}

// Add common HTTP method helpers to the apiClient function
apiClient.get = <T>(endpoint: string, options: RequestOptions = {}) =>
  apiClient<T>(endpoint, { ...options, method: 'GET' });

apiClient.post = <T>(endpoint: string, data?: any, options: RequestOptions = {}) =>
  apiClient<T>(endpoint, {
    ...options,
    method: 'POST',
    body: data instanceof FormData ? data : JSON.stringify(data),
  });

apiClient.put = <T>(endpoint: string, data?: any, options: RequestOptions = {}) =>
  apiClient<T>(endpoint, {
    ...options,
    method: 'PUT',
    body: data instanceof FormData ? data : JSON.stringify(data),
  });

apiClient.delete = <T>(endpoint: string, options: RequestOptions = {}) =>
  apiClient<T>(endpoint, { ...options, method: 'DELETE' });

