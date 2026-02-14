'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  ClipboardList,
  BookOpen,
  BarChart3,
  User,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  isCenter?: boolean;
}

const navigationItems: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: Home,
  },
  {
    label: 'Exam',
    href: '/exam',
    icon: ClipboardList,
  },
  {
    label: 'Journal',
    href: '/journal',
    icon: BookOpen,
    isCenter: true,
  },
  {
    label: 'Results',
    href: '/results',
    icon: BarChart3,
  },
  {
    label: 'Profile',
    href: '/profile',
    icon: User,
  },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 border-t border-border"
      aria-label="Mobile navigation"
    >
      <div className="flex items-end justify-around h-20 px-2 pb-2 safe-area-inset-bottom">
        {navigationItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
          const Icon = item.icon;

          if (item.isCenter) {
            return (
              <Link
                key={item.href}
                href={item.href}
                className="flex flex-col items-center justify-center group relative"
                aria-current={isActive ? 'page' : undefined}
              >
                {/* Elevated center button */}
                <div
                  className={cn(
                    'absolute -top-6 flex items-center justify-center w-14 h-14 rounded-2xl shadow-lg transition-all duration-200',
                    'ring-2 ring-background',
                    isActive
                      ? 'bg-primary text-primary-foreground scale-105'
                      : 'bg-card text-muted-foreground group-hover:bg-accent group-hover:text-accent-foreground group-hover:scale-105'
                  )}
                >
                  <Icon className="h-6 w-6" />
                </div>
                {/* Label */}
                <span
                  className={cn(
                    'text-[10px] font-medium transition-colors mt-10',
                    isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
                  )}
                >
                  {item.label}
                </span>
              </Link>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex flex-col items-center justify-center min-w-[64px] py-2 group"
              aria-current={isActive ? 'page' : undefined}
            >
              {/* Icon */}
              <div
                className={cn(
                  'flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-200',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground group-hover:bg-accent/50 group-hover:text-foreground'
                )}
              >
                <Icon className="h-5 w-5" />
              </div>
              {/* Label */}
              <span
                className={cn(
                  'text-[10px] font-medium mt-1 transition-colors',
                  isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
                )}
              >
                {item.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
