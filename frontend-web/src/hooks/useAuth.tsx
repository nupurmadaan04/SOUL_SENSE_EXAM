'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import {
    UserSession,
    getSession,
    saveSession,
    clearSession,
    getExpiryTimestamp
} from '@/lib/utils/sessionStorage';

interface AuthContextType {
    user: UserSession['user'] | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (email: string, rememberMe: boolean) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [user, setUser] = useState<UserSession['user'] | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        // Check for existing session on mount
        const session = getSession();
        if (session) {
            setUser(session.user);
        }
        setIsLoading(false);
    }, []);

    const login = async (email: string, rememberMe: boolean) => {
        setIsLoading(true);
        try {
            // Simulate API call
            await new Promise((resolve) => setTimeout(resolve, 1000));

            const mockUser = {
                id: '1',
                email,
                name: email.split('@')[0],
            };

            const session: UserSession = {
                user: mockUser,
                token: 'mock-jwt-token',
                expiresAt: getExpiryTimestamp(),
            };

            saveSession(session, rememberMe);
            setUser(mockUser);
            router.push('/dashboard');
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        } finally {
            setIsLoading(false);
        }
    };

    const logout = () => {
        clearSession();
        setUser(null);
        router.push('/login');
    };

    return (
        <AuthContext.Provider value={{
            user,
            isAuthenticated: !!user,
            isLoading,
            login,
            logout
        }}>
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
