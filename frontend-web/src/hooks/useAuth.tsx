'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import {
  UserSession,
  getSession,
  saveSession,
  clearSession,
  getExpiryTimestamp,
} from '@/lib/utils/sessionStorage';
import { authApi } from '@/lib/api/auth';

interface AuthContextType {
  user: UserSession['user'] | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isMockMode: boolean;
  login: (
    data: {
      username: string;
      password: string;
      captcha_input?: string;
      session_id?: string;
    },
    rememberMe: boolean
  ) => Promise<any>;
  login2FA: (data: { pre_auth_token: string; code: string }, rememberMe: boolean) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<UserSession['user'] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMockMode, setIsMockMode] = useState(false);
  const router = useRouter();

  useEffect(() => {
    // Check for existing session on mount
    const session = getSession();
    if (session) {
      setUser(session.user);
    }

    // Check if backend is in mock mode (from main)
    checkMockMode();

    setIsLoading(false);
  }, []);

  const checkMockMode = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/health`, {
        method: 'GET',
      });

      if (response.ok) {
        const data = await response.json();
        setIsMockMode(data.mock_auth_mode || false);
      }
    } catch (error) {
      console.warn('Could not check mock mode status:', error);
    }
  };

  const login = async (
    loginData: {
      username: string;
      password: string;
      captcha_input?: string;
      session_id?: string;
    },
    rememberMe: boolean
  ) => {
    setIsLoading(true);
    try {
      const result = await authApi.login(loginData);

      if (result.pre_auth_token) {
        return result; // 2FA Required
      }

      const session: UserSession = {
        user: {
          id: 'current',
          email: loginData.username.includes('@') ? loginData.username : '',
          name: 'User',
        },
        token: result.access_token,
        expiresAt: getExpiryTimestamp(),
      };

      saveSession(session, rememberMe);
      setUser(session.user);
      router.push('/dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const login2FA = async (data: { pre_auth_token: string; code: string }, rememberMe: boolean) => {
    setIsLoading(true);
    try {
      const result = await authApi.login2FA(data);

      const session: UserSession = {
        user: {
          id: 'current',
          email: '',
          name: 'User',
        },
        token: result.access_token,
        expiresAt: getExpiryTimestamp(),
      };

      saveSession(session, rememberMe);
      setUser(session.user);
      router.push('/dashboard');
    } catch (error) {
      console.error('2FA verification failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    // Integrate logout fetch from main
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      await fetch(`${apiUrl}/api/v1/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('Logout error:', error);
    }

    clearSession();
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        isMockMode,
        login,
        login2FA,
        logout,
      }}
    >
      {!isLoading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
