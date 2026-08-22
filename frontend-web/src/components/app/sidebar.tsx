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
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Menu,
  X,
} from 'lucide-react';
import {
  Button,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
  Avatar,
  AvatarFallback,
  AvatarImage,
} from '@/components/ui';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/hooks/useAuth';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  tooltip: string;
}

const navigationItems: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: <Home className="h-5 w-5" />,
    tooltip: 'View your emotional trends and insights',
  },
  {
    label: 'Take Exam',
    href: '/exam',
    icon: <ClipboardList className="h-5 w-5" />,
    tooltip: 'Start a new EQ assessment',
  },
  {
    label: 'Journal',
    href: '/journal',
    icon: <BookOpen className="h-5 w-5" />,
    tooltip: 'Write about your day and feelings',
  },
  {
    label: 'Results',
    href: '/results',
    icon: <BarChart3 className="h-5 w-5" />,
    tooltip: 'Analyze your assessment history',
  },
  {
    label: 'Profile',
    href: '/profile',
    icon: <User className="h-5 w-5" />,
    tooltip: 'Manage your personal patterns',
  },
  {
    label: 'Settings',
    href: '/settings',
    icon: <Settings className="h-5 w-5" />,
    tooltip: 'Configure app and privacy preferences',
  },
  {
    label: 'Help & Guide',
    href: '/settings#support',
    icon: <HelpCircle className="h-5 w-5" />,
    tooltip: 'User guide, FAQs and support',
  },
];

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = React.useState(false);
  const [isMobile, setIsMobile] = React.useState(false);
  const [isMobileOpen, setIsMobileOpen] = React.useState(false);
  const pathname = usePathname();
  const { user } = useAuth();

  // Detect mobile breakpoint separately from collapse state
  React.useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 767px)');

    const handleChange = (event: MediaQueryListEvent | MediaQueryList) => {
      const matches = event.matches;
      setIsMobile(matches);
      if (!matches) {
        setIsMobileOpen(false);
      }
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

  // Close mobile sidebar on route change
  React.useEffect(() => {
    setIsMobileOpen(false);
  }, [pathname]);

  const isActive = (href: string) => {
    const cleanHref = href.split('#')[0];
    if (cleanHref === '/dashboard') return pathname === '/dashboard';
    return pathname.startsWith(cleanHref);
  };

  const getUserInitials = (name?: string) => {
    if (!name) return 'U';
    return name
      .split(' ')
      .map((p) => p[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();
  };

  const toggleDesktopCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  const toggleMobileDrawer = () => {
    setIsMobileOpen(!isMobileOpen);
  };

  const closeMobileDrawer = () => {
    setIsMobileOpen(false);
  };

  // ─── MOBILE: Fixed off-canvas drawer with backdrop ─────────────────
  if (isMobile) {
    return (
      <TooltipProvider>
        {/* Hamburger trigger button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleMobileDrawer}
          className="fixed top-3 left-3 z-50 rounded-full bg-background/80 backdrop-blur-lg shadow-lg border border-border/40 hover:bg-muted/60"
          title="Open menu"
        >
          <Menu className="h-5 w-5" />
        </Button>

        {/* Backdrop overlay */}
        <AnimatePresence>
          {isMobileOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="fixed inset-0 z-[998] bg-black/50 backdrop-blur-sm"
              onClick={closeMobileDrawer}
              aria-hidden="true"
            />
          )}
        </AnimatePresence>

        {/* Sidebar drawer */}
        <aside
          className={cn(
            'fixed top-0 left-0 z-[999] flex flex-col h-screen w-72 bg-background/95 backdrop-blur-2xl shadow-2xl border-r border-border/40 overflow-x-hidden',
            'transition-transform duration-300 ease-in-out',
            isMobileOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border/40 px-4 py-5 mb-1 shrink-0">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-gradient-to-br from-primary to-secondary p-2 shadow-lg shadow-primary/20">
                <BookOpen className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
                Soul Sense
              </span>
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={closeMobileDrawer}
              className="rounded-full hover:bg-muted/50 transition-all duration-300"
              title="Close menu"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 space-y-1.5 overflow-y-auto overflow-x-hidden px-3 py-3">
            {navigationItems.map((item) => {
              const active = isActive(item.href);

              return (
                <div key={item.href}>
                  <Link href={item.href} onClick={closeMobileDrawer}>
                    <Button
                      variant="ghost"
                      className={cn(
                        'w-full transition-all duration-200 relative group justify-start gap-3.5 px-4 h-11 rounded-2xl',
                        active
                          ? 'bg-primary/15 text-primary font-bold shadow-xs'
                          : 'text-slate-700 dark:text-slate-200 hover:text-primary hover:bg-primary/10 font-semibold'
                      )}
                    >
                      {active && (
                        <div className="absolute left-0 w-[3px] h-6 bg-primary rounded-r-full" />
                      )}

                      <div
                        className={cn(
                          'transition-transform duration-200 shrink-0',
                          active
                            ? 'text-primary'
                            : 'text-slate-600 dark:text-slate-300 group-hover:text-primary'
                        )}
                      >
                        {item.icon}
                      </div>

                      <span
                        className={cn(
                          'text-sm font-bold transition-colors whitespace-nowrap',
                          active ? 'text-primary' : 'text-slate-800 dark:text-slate-100 group-hover:text-primary'
                        )}
                      >
                        {item.label}
                      </span>
                    </Button>
                  </Link>
                </div>
              );
            })}
          </nav>

          {/* User Profile Summary & Footer */}
          <div className="mt-auto p-3 space-y-2 shrink-0 border-t border-border/40 bg-muted/10">
            <Link href="/profile" onClick={closeMobileDrawer}>
              <div className="rounded-2xl p-2 transition-all duration-300 border border-transparent bg-muted/30 hover:bg-muted/50 hover:border-border/40 flex items-center gap-3">
                <Avatar className="h-9 w-9 border-2 border-background shadow-sm">
                  <AvatarFallback className="bg-gradient-to-br from-primary to-primary/70 text-white text-xs font-bold">
                    {getUserInitials(user?.name || user?.username)}
                  </AvatarFallback>
                </Avatar>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate leading-none mb-1">
                    {user?.name || user?.username || 'User'}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate font-medium">
                    @{user?.username || 'member'}
                  </p>
                </div>
              </div>
            </Link>

            <div className="px-2 py-1">
              <p className="text-[10px] text-center text-muted-foreground font-medium opacity-60">
                © 2026 Soul Sense EQ
              </p>
            </div>
          </div>
        </aside>
      </TooltipProvider>
    );
  }

  // ─── DESKTOP: In-flow sticky sidebar ─────────────────────────────
  return (
    <TooltipProvider>
      <aside
        className={cn(
          'flex flex-col h-screen sticky top-0 border-r border-border/60 bg-card/75 dark:bg-card/40 backdrop-blur-2xl shadow-sm transition-all duration-300 ease-in-out relative z-40 shrink-0 overflow-x-hidden select-none',
          isCollapsed ? 'w-20' : 'w-64'
        )}
      >
        {/* Header with Title and Collapse Button */}
        <div className="flex items-center justify-between border-b border-border/40 px-4 py-5 mb-1 shrink-0">
          {!isCollapsed && (
            <Link href="/dashboard" className="flex items-center gap-3">
              <div className="rounded-xl bg-gradient-to-br from-primary to-secondary p-2 shadow-lg shadow-primary/20">
                <BookOpen className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
                Soul Sense
              </span>
            </Link>
          )}

          <Button
            variant="ghost"
            size="icon"
            onClick={toggleDesktopCollapse}
            className={cn(
              'rounded-full hover:bg-muted/50 transition-all duration-300',
              isCollapsed ? 'mx-auto' : 'ml-auto'
            )}
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 space-y-1.5 overflow-y-auto overflow-x-hidden px-3 py-3">
          {navigationItems.map((item) => {
            const active = isActive(item.href);

            const NavButton = (
              <Button
                variant="ghost"
                className={cn(
                  'w-full transition-all duration-200 relative group h-11 rounded-2xl cursor-pointer',
                  isCollapsed ? 'justify-center px-0' : 'justify-start gap-3.5 px-4',
                  active
                    ? 'bg-primary/15 text-primary font-bold shadow-xs'
                    : 'text-slate-700 dark:text-slate-200 hover:text-primary hover:bg-primary/10 font-semibold'
                )}
              >
                {/* Active Indicator Line */}
                {active && (
                  <div className="absolute left-0 w-[3px] h-6 bg-primary rounded-r-full" />
                )}

                <div
                  className={cn(
                    'transition-transform duration-200 shrink-0',
                    active
                      ? 'text-primary'
                      : 'text-slate-600 dark:text-slate-300 group-hover:text-primary'
                  )}
                >
                  {item.icon}
                </div>

                {!isCollapsed && (
                  <span
                    className={cn(
                      'text-sm font-bold transition-colors whitespace-nowrap',
                      active ? 'text-primary' : 'text-slate-800 dark:text-slate-100 group-hover:text-primary'
                    )}
                  >
                    {item.label}
                  </span>
                )}
              </Button>
            );

            return (
              <div key={item.href}>
                {isCollapsed ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Link href={item.href}>
                        {NavButton}
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent side="right" className="bg-popover text-popover-foreground border shadow-md font-semibold text-xs py-1.5 px-3">
                      <p className="font-bold">{item.label}</p>
                      <p className="text-[11px] opacity-80">{item.tooltip}</p>
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <Link href={item.href}>
                    {NavButton}
                  </Link>
                )}
              </div>
            );
          })}
        </nav>

        {/* User Profile Summary & Footer Section */}
        <div className="mt-auto p-3 space-y-2 shrink-0 border-t border-border/40 bg-muted/10">
          <Link href="/profile">
            <div
              className={cn(
                'rounded-2xl p-2 transition-all duration-300 border border-transparent cursor-pointer',
                !isCollapsed && 'bg-muted/30 hover:bg-muted/60 hover:border-border/40'
              )}
            >
              <div className={cn('flex items-center gap-3', isCollapsed ? 'justify-center' : 'px-2')}>
                <Avatar className="h-9 w-9 border-2 border-background shadow-sm shrink-0">
                  <AvatarFallback className="bg-gradient-to-br from-primary to-primary/70 text-white text-xs font-bold">
                    {getUserInitials(user?.name || user?.username)}
                  </AvatarFallback>
                </Avatar>

                {!isCollapsed && (
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate leading-none mb-1 text-foreground">
                      {user?.name || user?.username || 'User'}
                    </p>
                    <p className="text-[10px] text-muted-foreground truncate font-medium">
                      @{user?.username || 'member'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </Link>

          {!isCollapsed && (
            <div className="px-2 py-1">
              <p className="text-[10px] text-center text-muted-foreground font-medium opacity-60">
                © 2026 Soul Sense EQ
              </p>
            </div>
          )}
        </div>
      </aside>
    </TooltipProvider>
  );
}
