/**
 * Session storage utilities for handling user persistence
 */

const SESSION_KEY = 'soul_sense_auth_session';
const SESSION_EXPIRY_DAYS = 30;

export interface UserSession {
    user: {
        id: string;
        email: string;
        name?: string;
    };
    token: string;
    expiresAt: number;
}

/**
 * Save session to storage
 * @param session User session data
 * @param rememberMe Whether to use localStorage (persistent) or sessionStorage (per-tab)
 */
export const saveSession = (session: UserSession, rememberMe: boolean): void => {
    const data = JSON.stringify(session);
    if (rememberMe) {
        localStorage.setItem(SESSION_KEY, data);
    } else {
        sessionStorage.setItem(SESSION_KEY, data);
    }
};

/**
 * Get session from storage
 * Checks both localStorage and sessionStorage
 */
export const getSession = (): UserSession | null => {
    const localData = localStorage.getItem(SESSION_KEY);
    const sessionData = sessionStorage.getItem(SESSION_KEY);

    const data = localData || sessionData;
    if (!data) return null;

    try {
        const session: UserSession = JSON.parse(data);

        // Validate expiry
        if (Date.now() > session.expiresAt) {
            clearSession();
            return null;
        }

        return session;
    } catch (error) {
        console.error('Failed to parse session data:', error);
        clearSession();
        return null;
    }
};

/**
 * Clear session from both storage types
 */
export const clearSession = (): void => {
    localStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem(SESSION_KEY);
};

/**
 * Calculate expiry timestamp
 */
export const getExpiryTimestamp = (): number => {
    const now = new Date();
    now.setDate(now.getDate() + SESSION_EXPIRY_DAYS);
    return now.getTime();
};
