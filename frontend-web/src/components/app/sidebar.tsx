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
];

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = React.useState(false);
  const [isMobile, setIsMobile] = React.useState(false);
  const [isMobileOpen, setIsMobileOpen] = React.useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // Detect mobile breakpoint separately from collapse state
  React.useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 767px)');

    const handleChange = (event: MediaQueryListEvent | MediaQueryList) => {
      const matches = event.matches;
      setIsMobile(matches);
      // Auto-close mobile drawer when switching to desktop
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
    return pathname.startsWith(href);
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
        {/* Hamburger trigger button — always visible on mobile */}
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

        {/* Sidebar drawer — slides in/out via translate */}
        <aside
          className={cn(
            'fixed top-0 left-0 z-[999] flex flex-col h-screen w-72 bg-background/95 backdrop-blur-2xl shadow-2xl border-r border-border/40',
            'transition-transform duration-300 ease-in-out',
            isMobileOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          {/* Decorative Background Elements */}
          <div className="absolute inset-0 overflow-hidden pointer-events-none -z-10">
            <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[30%] bg-primary/5 blur-[80px] rounded-full" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[30%] bg-secondary/5 blur-[80px] rounded-full" />
          </div>

          {/* Header with Title and Close Button */}
          <div className="flex items-center justify-between border-b border-border/40 px-4 py-6 mb-2">
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3"
            >
              <div className="rounded-xl bg-gradient-to-br from-primary to-secondary p-2 shadow-lg shadow-primary/20">
                <BookOpen className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
                Soul Sense
              </span>
            </motion.div>

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
          <nav className="flex-1 space-y-1.5 overflow-y-auto px-3 py-4">
            {navigationItems.map((item) => {
              const active = isActive(item.href);

              return (
                <div key={item.href}>
                  <Link href={item.href}>
                    <motion.div
                      whileHover={{ x: 4 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <Button
                        variant="ghost"
                        className={cn(
                          'w-full transition-all duration-300 relative group overflow-hidden justify-start gap-4 px-4',
                          active
                            ? 'bg-primary/5 text-primary font-medium'
                            : 'text-muted-foreground hover:text-foreground hover:bg-muted/30'
                        )}
                      >
                        {active && (
                          <motion.div
                            layoutId="sidebar-mobile-active-tab"
                            className="absolute left-0 w-[3px] h-5 bg-primary rounded-r-full"
                            transition={{ type: 'tween', ease: 'easeOut', duration: 0.3 }}
                          />
                        )}

                        <div
                          className={cn(
                            'transition-colors duration-300',
                            active
                              ? 'text-primary'
                              : 'text-muted-foreground group-hover:text-foreground'
                          )}
                        >
                          {item.icon}
                        </div>

                        <motion.span
                          initial={{ opacity: 0, x: -5 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="text-sm"
                        >
                          {item.label}
                        </motion.span>
                      </Button>
                    </motion.div>
                  </Link>
                </div>
              );
            })}
          </nav>

          {/* User Profile Summary & Footer Section */}
          <div className="mt-auto p-3 space-y-4">
            <div className="rounded-2xl p-2 transition-all duration-300 border border-transparent bg-muted/30 hover:bg-muted/50 hover:border-border/40">
              <div className="flex items-center gap-3 px-2">
                <Avatar className="h-9 w-9 border-2 border-background shadow-sm">
                  <AvatarFallback className="bg-gradient-to-br from-primary/80 to-secondary/80 text-white text-xs font-bold">
                    {getUserInitials(user?.name)}
                  </AvatarFallback>
                </Avatar>

                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex-1 min-w-0"
                >
                  <p className="text-sm font-semibold truncate leading-none mb-1">
                    {user?.name || 'User'}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate uppercase tracking-wider font-medium">
                    {user?.username || 'Free Member'}
                  </p>
                </motion.div>
              </div>
            </div>

            <div className="px-4 py-2">
              <p className="text-[10px] text-center text-muted-foreground font-medium opacity-60">
                © 2026 Soul Sense EQ
              </p>
            </div>
          </div>
        </aside>
      </TooltipProvider>
    );
  }

  // ─── DESKTOP: In-flow sidebar with icon-strip collapse ─────────────
  return (
    <TooltipProvider>
      <aside
        className={cn(
          'flex flex-col h-screen border-r border-border/40 bg-background/40 backdrop-blur-2xl shadow-sm transition-all duration-500 ease-in-out relative z-40 flex-shrink-0',
          isCollapsed ? 'w-20' : 'w-64'
        )}
      >
        {/* Decorative Background Elements */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none -z-10">
          <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[30%] bg-primary/5 blur-[80px] rounded-full" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[30%] bg-secondary/5 blur-[80px] rounded-full" />
        </div>

        {/* Header with Title and Collapse Button */}
        <div className="flex items-center justify-between border-b border-border/40 px-4 py-6 mb-2">
          <AnimatePresence mode="wait">
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="flex items-center gap-3"
              >
                <div className="rounded-xl bg-gradient-to-br from-primary to-secondary p-2 shadow-lg shadow-primary/20">
                  <BookOpen className="h-5 w-5 text-white" />
                </div>
                <span className="text-lg font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/70">
                  Soul Sense
                </span>
              </motion.div>
            )}
          </AnimatePresence>
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
        <nav className="flex-1 space-y-1.5 overflow-y-auto px-3 py-4">
          {navigationItems.map((item) => {
            const active = isActive(item.href);

            return (
              <div key={item.href}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Link href={item.href}>
                      <motion.div
                        whileHover={{ x: isCollapsed ? 0 : 4 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        <Button
                          variant="ghost"
                          className={cn(
                            'w-full transition-all duration-300 relative group overflow-hidden',
                            isCollapsed ? 'justify-center px-0' : 'justify-start gap-4 px-4',
                            active
                              ? 'bg-primary/5 text-primary font-medium'
                              : 'text-muted-foreground hover:text-foreground hover:bg-muted/30'
                          )}
                        >
                          {/* Active Indicator Line */}
                          {active && (
                            <motion.div
                              layoutId="sidebar-active-tab"
                              className="absolute left-0 w-[3px] h-5 bg-primary rounded-r-full"
                              transition={{ type: 'tween', ease: 'easeOut', duration: 0.3 }}
                            />
                          )}

                          <div
                            className={cn(
                              'transition-colors duration-300',
                              active
                                ? 'text-primary'
                                : 'text-muted-foreground group-hover:text-foreground'
                            )}
                          >
                            {item.icon}
                          </div>

                          {!isCollapsed && (
                            <motion.span
                              initial={{ opacity: 0, x: -5 }}
                              animate={{ opacity: 1, x: 0 }}
                              className="text-sm"
                            >
                              {item.label}
                            </motion.span>
                          )}
                        </Button>
                      </motion.div>
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <div className="flex flex-col gap-1">
                      <p className="font-bold">{item.label}</p>
                      <p className="text-xs opacity-70">{item.tooltip}</p>
                    </div>
                  </TooltipContent>
                </Tooltip>
              </div>
            );
          })}
        </nav>

        {/* User Profile Summary & Footer Section */}
        <div className="mt-auto p-3 space-y-4">
          <div
            className={cn(
              'rounded-2xl p-2 transition-all duration-300 border border-transparent',
              !isCollapsed && 'bg-muted/30 hover:bg-muted/50 hover:border-border/40'
            )}
          >
            <div className={cn('flex items-center gap-3', isCollapsed ? 'justify-center' : 'px-2')}>
              <Avatar className="h-9 w-9 border-2 border-background shadow-sm">
                <AvatarFallback className="bg-gradient-to-br from-primary/80 to-secondary/80 text-white text-xs font-bold">
                  {getUserInitials(user?.name)}
                </AvatarFallback>
              </Avatar>

              {!isCollapsed && (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex-1 min-w-0"
                >
                  <p className="text-sm font-semibold truncate leading-none mb-1">
                    {user?.name || 'User'}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate uppercase tracking-wider font-medium">
                    {user?.username || 'Free Member'}
                  </p>
                </motion.div>
              )}
            </div>
          </div>

          {!isCollapsed && (
            <div className="px-4 py-2">
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
