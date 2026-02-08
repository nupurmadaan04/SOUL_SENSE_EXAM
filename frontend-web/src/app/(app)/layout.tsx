'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
// Requirement: Use the existing auth context/hook
import { useAuth } from '@/hooks/useAuth'; 

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Requirement: Check authentication status
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Requirement: Redirect to /login if user is not authenticated
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  // Requirement: Include a loading state while auth check is in progress
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50 dark:bg-gray-900">
        <div className="w-12 h-12 border-4 border-blue-200 rounded-full animate-spin border-t-blue-600"></div>
      </div>
    );
  }

  // Double check: If not authenticated, return null (the redirect above handles the move)
  if (!isAuthenticated) {
    return null;
  }

  // Requirement: Wrap children with sidebar and header components (placeholders)
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      
      {/* SIDEBAR PLACEHOLDER */}
      <aside className="hidden md:flex flex-col w-64 border-r border-gray-200 bg-white dark:bg-gray-950 dark:border-gray-800 p-4">
        <div className="text-sm font-medium text-gray-400 border-2 border-dashed border-gray-300 rounded-lg h-full flex items-center justify-center">
          Sidebar Placeholder
        </div>
      </aside>

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        
        {/* HEADER PLACEHOLDER */}
        <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200 dark:bg-gray-950 dark:border-gray-800 h-16">
          <h1 className="text-xl font-semibold">Dashboard</h1>
          <div className="w-8 h-8 bg-gray-200 rounded-full dark:bg-gray-800"></div>
        </header>

        {/* MAIN CONTENT AREA */}
        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}