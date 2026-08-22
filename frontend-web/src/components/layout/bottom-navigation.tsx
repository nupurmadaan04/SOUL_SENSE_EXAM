'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Brain,
  FileText,
  User,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';
import { useHapticFeedback } from '@/hooks/useMobileGestures';

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Assessment', href: '/exam', icon: Brain },
  { name: 'Journal', href: '/journal', icon: FileText },
  { name: 'Profile', href: '/profile', icon: User },
];

export function BottomNavigation() {
  const pathname = usePathname();
  const { light } = useHapticFeedback();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const handleNavClick = () => {
    light();
  };

  if (!mounted) return null;

  const isPublic = pathname === '/' || pathname.startsWith('/community') || pathname.startsWith('/faq') || pathname.startsWith('/terms') || pathname.startsWith('/privacy') || pathname.startsWith('/login') || pathname.startsWith('/register') || pathname.startsWith('/forgot-password');
  if (isPublic) return null;

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 md:hidden"
      aria-label="Mobile navigation"
    >
      <div className="bg-background/95 backdrop-blur-lg border-t border-border safe-area-bottom">
        <div className="flex items-center justify-around px-2 py-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={handleNavClick}
                className={cn(
                  'relative flex flex-col items-center justify-center min-w-touch min-h-touch py-2 px-3 rounded-lg transition-colors touch-manipulation',
                  isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                {isActive && (
                  <motion.div
                    layoutId="mobile-bottom-nav-indicator"
                    className="absolute inset-0 bg-primary/10 rounded-lg"
                    initial={false}
                    transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                  />
                )}
                <Icon className="h-5 w-5 relative z-10" aria-hidden="true" />
                <span className="text-[10px] font-medium mt-1 relative z-10">
                  {item.name}
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

export function MobileFab() {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const { light, medium } = useHapticFeedback();

  const actions = [
    { name: 'New Entry', href: '/journal/new', icon: FileText },
    { name: 'Take Test', href: '/exam', icon: Brain },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  return (
    <div className="fixed bottom-20 right-4 z-40 md:hidden">
      <div className="relative">
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="absolute bottom-16 right-0 flex flex-col-reverse gap-2"
          >
            {actions.map((action, index) => (
              <motion.div
                key={action.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Link
                  href={action.href}
                  onClick={() => {
                    light();
                    setIsExpanded(false);
                  }}
                  className="flex items-center gap-3 bg-card border border-border rounded-full pl-4 pr-3 py-2 shadow-lg touch-manipulation min-h-touch"
                >
                  <span className="text-sm font-medium">{action.name}</span>
                  <action.icon className="h-4 w-4 text-primary" />
                </Link>
              </motion.div>
            ))}
          </motion.div>
        )}

        <button
          onClick={() => {
            medium();
            setIsExpanded(!isExpanded);
          }}
          className={cn(
            'w-14 h-14 rounded-full flex items-center justify-center shadow-lg touch-manipulation transition-transform active:scale-95',
            'bg-gradient-to-br from-primary to-secondary text-white',
            isExpanded && 'rotate-45'
          )}
          aria-expanded={isExpanded}
          aria-label="Quick actions menu"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
