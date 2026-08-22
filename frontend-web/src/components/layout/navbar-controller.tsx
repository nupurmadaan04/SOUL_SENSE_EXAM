'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useMounted } from '@/hooks/useMounted';

// Use dynamic import with ssr: false to prevent hydration mismatch
// on the floating navbar which depends on complex client-side state
const FloatingNavbar = dynamic(
  () => import('./floating-navbar').then((mod) => mod.FloatingNavbar),
  { ssr: false }
);

/**
 * Conditionally renders the floating navbar based on pathname.
 * We hide it on authentication-related pages to prevent visual overlap
 * and redundant "Sign In" CTA on the login/register flows.
 */
export function NavbarController() {
  const pathname = usePathname();
  const isMounted = useMounted();

  if (!isMounted) {
    return null;
  }

  // App routes have their own internal Header & Sidebar layout
  // Auth routes have clean focused authentication forms
  const isAppRoute = pathname.startsWith('/dashboard') ||
    pathname.startsWith('/profile') ||
    pathname.startsWith('/settings') ||
    pathname.startsWith('/exam') ||
    pathname.startsWith('/results') ||
    pathname.startsWith('/journal') ||
    pathname.startsWith('/welcome') ||
    pathname.startsWith('/analytics') ||
    pathname.startsWith('/admin') ||
    pathname.startsWith('/login') ||
    pathname.startsWith('/register') ||
    pathname.startsWith('/forgot-password') ||
    pathname.startsWith('/reset-password');

  if (isAppRoute) {
    return null;
  }

  // Public marketing & community routes (e.g., '/', '/community', '/faq', '/terms', '/privacy', '/contact')
  return <FloatingNavbar />;
}
