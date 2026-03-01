/**
 * @jest-environment jsdom
 * 
 * Session Storage Utility Tests (Issue #999)
 * ------------------------------------------
 * Tests for session storage utilities including activity tracking.
 */

import {
  saveSession,
  getSession,
  clearSession,
  getExpiryTimestamp,
  updateLastActivity,
  getLastActivity,
  isSessionTimedOut,
  getRemainingTime,
  clearLastActivity,
  SESSION_KEY,
} from '../sessionStorage';

// Mock UserSession data
const mockUserSession = {
  user: {
    id: '123',
    email: 'test@example.com',
    username: 'testuser',
    name: 'Test User',
    created_at: '2024-01-01T00:00:00Z',
    onboarding_completed: true,
  },
  token: 'mock-token-123',
  expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000, // 30 days
};

describe('Session Storage - Basic Operations', () => {
  beforeEach(() => {
    // Clear all storage before each test
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('saveSession', () => {
    it('should save session to localStorage when rememberMe is true', () => {
      saveSession(mockUserSession, true);

      const saved = localStorage.getItem('soul_sense_auth_session');
      expect(saved).toBeTruthy();
      expect(JSON.parse(saved!)).toEqual(mockUserSession);
    });

    it('should save session to sessionStorage when rememberMe is false', () => {
      saveSession(mockUserSession, false);

      const saved = sessionStorage.getItem('soul_sense_auth_session');
      expect(saved).toBeTruthy();
      expect(JSON.parse(saved!)).toEqual(mockUserSession);
    });

    it('should clear duplicate storage when saving', () => {
      // Save to both first
      localStorage.setItem('soul_sense_auth_session', JSON.stringify(mockUserSession));
      sessionStorage.setItem('soul_sense_auth_session', JSON.stringify(mockUserSession));

      // Save with rememberMe=false should clear localStorage
      saveSession(mockUserSession, false);
      expect(localStorage.getItem('soul_sense_auth_session')).toBeNull();
      expect(sessionStorage.getItem('soul_sense_auth_session')).toBeTruthy();
    });
  });

  describe('getSession', () => {
    it('should return null when no session exists', () => {
      const session = getSession();
      expect(session).toBeNull();
    });

    it('should return session from localStorage', () => {
      localStorage.setItem('soul_sense_auth_session', JSON.stringify(mockUserSession));
      
      const session = getSession();
      expect(session).toEqual(mockUserSession);
    });

    it('should return session from sessionStorage', () => {
      sessionStorage.setItem('soul_sense_auth_session', JSON.stringify(mockUserSession));
      
      const session = getSession();
      expect(session).toEqual(mockUserSession);
    });

    it('should return null and clear storage for expired session', () => {
      const expiredSession = {
        ...mockUserSession,
        expiresAt: Date.now() - 1000, // Expired 1 second ago
      };
      localStorage.setItem('soul_sense_auth_session', JSON.stringify(expiredSession));

      const session = getSession();
      expect(session).toBeNull();
      expect(localStorage.getItem('soul_sense_auth_session')).toBeNull();
    });

    it('should return null for invalid JSON', () => {
      localStorage.setItem('soul_sense_auth_session', 'invalid-json');

      const session = getSession();
      expect(session).toBeNull();
    });
  });

  describe('clearSession', () => {
    it('should clear session from both storages', () => {
      localStorage.setItem('soul_sense_auth_session', JSON.stringify(mockUserSession));
      sessionStorage.setItem('soul_sense_auth_session', JSON.stringify(mockUserSession));

      clearSession();

      expect(localStorage.getItem('soul_sense_auth_session')).toBeNull();
      expect(sessionStorage.getItem('soul_sense_auth_session')).toBeNull();
    });
  });

  describe('getExpiryTimestamp', () => {
    it('should return timestamp 30 days in the future', () => {
      const before = Date.now();
      const expiry = getExpiryTimestamp();
      const after = Date.now();

      const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000;
      expect(expiry).toBeGreaterThanOrEqual(before + thirtyDaysMs);
      expect(expiry).toBeLessThanOrEqual(after + thirtyDaysMs + 1000); // 1s tolerance
    });
  });
});

describe('Session Storage - Activity Tracking (Issue #999)', () => {
  const LAST_ACTIVITY_KEY = 'soul_sense_last_activity';

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('updateLastActivity', () => {
    it('should store current timestamp in both storages', () => {
      const before = Date.now();
      updateLastActivity();
      const after = Date.now();

      const localActivity = localStorage.getItem(LAST_ACTIVITY_KEY);
      const sessionActivity = sessionStorage.getItem(LAST_ACTIVITY_KEY);

      expect(localActivity).toBeTruthy();
      expect(sessionActivity).toBeTruthy();
      expect(localActivity).toEqual(sessionActivity);

      const timestamp = parseInt(localActivity!, 10);
      expect(timestamp).toBeGreaterThanOrEqual(before);
      expect(timestamp).toBeLessThanOrEqual(after);
    });

    it('should update timestamp on each call', () => {
      updateLastActivity();
      const firstTimestamp = parseInt(localStorage.getItem(LAST_ACTIVITY_KEY)!, 10);

      jest.advanceTimersByTime(5000); // Advance 5 seconds

      updateLastActivity();
      const secondTimestamp = parseInt(localStorage.getItem(LAST_ACTIVITY_KEY)!, 10);

      expect(secondTimestamp).toBeGreaterThan(firstTimestamp);
      expect(secondTimestamp - firstTimestamp).toBeGreaterThanOrEqual(5000);
    });
  });

  describe('getLastActivity', () => {
    it('should return null when no activity recorded', () => {
      const activity = getLastActivity();
      expect(activity).toBeNull();
    });

    it('should return timestamp from sessionStorage when available', () => {
      const timestamp = Date.now().toString();
      sessionStorage.setItem(LAST_ACTIVITY_KEY, timestamp);

      const activity = getLastActivity();
      expect(activity).toBe(parseInt(timestamp, 10));
    });

    it('should return timestamp from localStorage as fallback', () => {
      const timestamp = Date.now().toString();
      localStorage.setItem(LAST_ACTIVITY_KEY, timestamp);

      const activity = getLastActivity();
      expect(activity).toBe(parseInt(timestamp, 10));
    });

    it('should prefer sessionStorage over localStorage', () => {
      const sessionTimestamp = '1000';
      const localTimestamp = '2000';
      
      sessionStorage.setItem(LAST_ACTIVITY_KEY, sessionTimestamp);
      localStorage.setItem(LAST_ACTIVITY_KEY, localTimestamp);

      const activity = getLastActivity();
      expect(activity).toBe(1000); // Should use sessionStorage value
    });

    it('should return null for invalid timestamp', () => {
      localStorage.setItem(LAST_ACTIVITY_KEY, 'invalid');

      const activity = getLastActivity();
      expect(activity).toBeNull();
    });
  });

  describe('isSessionTimedOut', () => {
    it('should return true when no activity recorded', () => {
      const timedOut = isSessionTimedOut();
      expect(timedOut).toBe(true);
    });

    it('should return false when activity is recent', () => {
      updateLastActivity();
      
      const timedOut = isSessionTimedOut(15 * 60 * 1000); // 15 min timeout
      expect(timedOut).toBe(false);
    });

    it('should return true when activity is past timeout', () => {
      const pastTime = Date.now() - (16 * 60 * 1000); // 16 minutes ago
      localStorage.setItem(LAST_ACTIVITY_KEY, pastTime.toString());

      const timedOut = isSessionTimedOut(15 * 60 * 1000); // 15 min timeout
      expect(timedOut).toBe(true);
    });

    it('should use default timeout of 15 minutes', () => {
      const fourteenMinutesAgo = Date.now() - (14 * 60 * 1000);
      localStorage.setItem(LAST_ACTIVITY_KEY, fourteenMinutesAgo.toString());

      // Should not timeout at 14 minutes (default is 15)
      expect(isSessionTimedOut()).toBe(false);

      // Set to 16 minutes ago
      const sixteenMinutesAgo = Date.now() - (16 * 60 * 1000);
      localStorage.setItem(LAST_ACTIVITY_KEY, sixteenMinutesAgo.toString());

      // Should timeout at 16 minutes
      expect(isSessionTimedOut()).toBe(true);
    });
  });

  describe('getRemainingTime', () => {
    it('should return 0 when no activity recorded', () => {
      const remaining = getRemainingTime();
      expect(remaining).toBe(0);
    });

    it('should return full timeout when activity just occurred', () => {
      updateLastActivity();
      
      const timeout = 15 * 60 * 1000;
      const remaining = getRemainingTime(timeout);
      
      // Should be close to full timeout (allowing small execution time)
      expect(remaining).toBeGreaterThan(timeout - 1000);
      expect(remaining).toBeLessThanOrEqual(timeout);
    });

    it('should return 0 when timed out', () => {
      const pastTime = Date.now() - (20 * 60 * 1000); // 20 minutes ago
      localStorage.setItem(LAST_ACTIVITY_KEY, pastTime.toString());

      const remaining = getRemainingTime(15 * 60 * 1000);
      expect(remaining).toBe(0);
    });

    it('should return correct remaining time', () => {
      const fiveMinutesAgo = Date.now() - (5 * 60 * 1000);
      localStorage.setItem(LAST_ACTIVITY_KEY, fiveMinutesAgo.toString());

      const timeout = 15 * 60 * 1000;
      const remaining = getRemainingTime(timeout);
      
      // Should be around 10 minutes remaining
      expect(remaining).toBeGreaterThanOrEqual(9 * 60 * 1000);
      expect(remaining).toBeLessThanOrEqual(10 * 60 * 1000);
    });
  });

  describe('clearLastActivity', () => {
    it('should clear activity from both storages', () => {
      updateLastActivity();
      
      expect(localStorage.getItem(LAST_ACTIVITY_KEY)).toBeTruthy();
      expect(sessionStorage.getItem(LAST_ACTIVITY_KEY)).toBeTruthy();

      clearLastActivity();

      expect(localStorage.getItem(LAST_ACTIVITY_KEY)).toBeNull();
      expect(sessionStorage.getItem(LAST_ACTIVITY_KEY)).toBeNull();
    });
  });
});

describe('Session Storage - Integration', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('should maintain separate session and activity data', () => {
    // Save session
    saveSession(mockUserSession, true);
    
    // Update activity
    updateLastActivity();

    // Both should exist independently
    expect(getSession()).toEqual(mockUserSession);
    expect(getLastActivity()).toBeTruthy();

    // Clear session should not clear activity
    clearSession();
    expect(getSession()).toBeNull();
    expect(getLastActivity()).toBeTruthy();

    // Clear activity
    clearLastActivity();
    expect(getLastActivity()).toBeNull();
  });

  it('should detect timeout independently of session expiry', () => {
    // Save valid session
    saveSession(mockUserSession, true);
    
    // Set old activity (past timeout)
    const oldActivity = Date.now() - (20 * 60 * 1000);
    localStorage.setItem('soul_sense_last_activity', oldActivity.toString());

    // Session is valid but timed out due to inactivity
    expect(getSession()).toEqual(mockUserSession);
    expect(isSessionTimedOut()).toBe(true);
  });
});
