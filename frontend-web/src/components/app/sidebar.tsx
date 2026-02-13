'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  BookOpen,
  ClipboardList,
  BarChart3,
  User,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Button, Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui';
import { cn } from '@/lib/utils';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

const navigationItems: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: <Home className="h-5 w-5" />,
  },
  {
    label: 'Take Exam',
    href: '/exam',
    icon: <ClipboardList className="h-5 w-5" />,
  },
  {
    label: 'Journal',
    href: '/journal',
    icon: <BookOpen className="h-5 w-5" />,
  },
  {
    label: 'Results',
    href: '/results',
    icon: <BarChart3 className="h-5 w-5" />,
  },
  {
    label: 'Profile',
    href: '/profile',
    icon: <User className="h-5 w-5" />,
  },
  {
    label: 'Settings',
    href: '/settings',
    icon: <Settings className="h-5 w-5" />,
  },
];

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = React.useState(false);
  const pathname = usePathname();

  React.useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 767px)');

    const handleChange = (event: MediaQueryListEvent | MediaQueryList) => {
      const matches = event.matches;
      setIsCollapsed(matches);
    };

    handleChange(mediaQuery);

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
    } else {
      mediaQuery.addListener(handleChange);
    }

    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handleChange);
      } else {
        mediaQuery.removeListener(handleChange);
      }
    };
  }, []);

  const isActive = (href: string) => {
    return pathname.startsWith(href);
  };

  return (
    <TooltipProvider>
      <aside
        className={cn(
          'flex flex-col h-screen border-r bg-background transition-all duration-300 ease-in-out',
          isCollapsed ? 'w-16 md:w-20' : 'w-64'
        )}
      >
        {/* Header with Title and Collapse Button */}
        <div className="flex items-center justify-between border-b px-4 py-6">
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-primary/10 p-2">
                <BookOpen className="h-5 w-5 text-primary" />
              </div>
              <span className="text-sm font-semibold tracking-tight">Soul Sense</span>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="ml-auto"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 space-y-2 overflow-y-auto px-3 py-4">
          {navigationItems.map((item) => {
            const active = isActive(item.href);

            if (isCollapsed) {
              return (
                <div key={item.href}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Link href={item.href}>
                        <Button
                          variant={active ? 'default' : 'ghost'}
                          size="icon"
                          className={cn(
                            'w-full',
                            active && 'bg-primary text-primary-foreground hover:bg-primary/90'
                          )}
                          title={item.label}
                        >
                          {item.icon}
                        </Button>
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent>{item.label}</TooltipContent>
                  </Tooltip>
                </div>
              );
            }

            return (
              <Link key={item.href} href={item.href}>
                <Button
                  variant={active ? 'default' : 'ghost'}
                  className={cn(
                    'w-full justify-start gap-3',
                    active && 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm'
                  )}
                >
                  {item.icon}
                  <span className="text-sm font-medium">{item.label}</span>
                </Button>
              </Link>
            );
          })}
        </nav>

        {/* Footer Section */}
        <div className="border-t px-3 py-4">
          {!isCollapsed && (
            <p className="text-xs text-muted-foreground text-center">
              © 2026 Soul Sense
            </p>
          )}
        </div>
      </aside>
    </TooltipProvider>
  );
}
