'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Menu,
  X,
  BookOpen,
  Rocket,
  Sun,
  Moon,
  LayoutDashboard,
  Brain,
  FileText,
  Search,
  Library,
  User,
  Settings,
  LogOut,
  ChevronDown,
  Star,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui';
import { useTheme } from 'next-themes';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

const guestNavigation = [
  { name: 'Features', href: '/#features', icon: Rocket },
  { name: 'Testimonials', href: '/#testimonials', icon: Star },
  { name: 'About', href: '/#about', icon: Info },
];

const authenticatedNavigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Assessment', href: '/exam', icon: Brain },
  { name: 'Journal', href: '/journal', icon: FileText },
  { name: 'Deep Dive', href: '/assessments', icon: Search },
  { name: 'History', href: '/history', icon: Library },
];

import { useAuth } from '@/hooks/useAuth';

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [userMenuOpen, setUserMenuOpen] = React.useState(false);
  const { setTheme, theme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  const { isAuthenticated, logout, user, isLoading } = useAuth();
  const pathname = usePathname();
  const userMenuRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => setMounted(true), []);

  // Close user menu on click outside
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const navLinks = isAuthenticated ? authenticatedNavigation : guestNavigation;

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b bg-background/80 backdrop-blur-md">
      <nav
        id="navigation"
        className="container mx-auto flex items-center justify-between p-4 lg:px-8"
        aria-label="Main navigation"
        role="navigation"
      >
        <div className="flex lg:flex-1">
          <Link
            href="/"
            className="-m-1.5 p-1.5 flex items-center gap-2.5 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Soul Sense Home"
          >
            <div className="rounded-xl bg-gradient-to-br from-primary to-secondary p-2 shadow-lg shadow-primary/20 text-white group-hover:scale-105 transition-transform">
              <BookOpen className="h-5 w-5" aria-hidden="true" />
            </div>
            <span className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary">
              Soul Sense
            </span>
          </Link>
        </div>

        <div className="flex lg:hidden gap-4">
          {mounted && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>
          )}
          <button
            type="button"
            className="-m-2.5 inline-flex items-center justify-center rounded-md p-2.5 text-foreground hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={() => setMobileMenuOpen(true)}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-menu"
          >
            <span className="sr-only">Open main menu</span>
            <Menu className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>

        <div className="hidden lg:flex lg:gap-x-12" role="menubar">
          {!isLoading &&
            navLinks.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'group flex items-center gap-x-2 text-sm font-semibold leading-6 transition-colors rounded-md px-2 py-1',
                    isActive ? 'text-primary bg-primary/10' : 'text-foreground/70 hover:text-primary hover:bg-accent'
                  )}
                  aria-current={isActive ? 'page' : undefined}
                  role="menuitem"
                >
                  {Icon && (
                    <Icon
                      className={cn(
                        'h-4 w-4 transition-colors',
                        isActive ? 'text-primary' : 'text-foreground/50 group-hover:text-primary'
                      )}
                      aria-hidden="true"
                    />
                  )}
                  <span>{item.name}</span>
                </Link>
              );
            })}
        </div>

        <div className="hidden lg:flex lg:flex-1 lg:justify-end lg:items-center lg:gap-4">
          {mounted && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="rounded-full"
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>
          )}

          {!isLoading && isAuthenticated ? (
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 p-1 pl-2 rounded-full border hover:bg-accent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-expanded={userMenuOpen}
                aria-haspopup="menu"
                id="user-menu-button"
              >
                <div className="flex flex-col items-end mr-1" aria-hidden="true">
                  <span className="text-sm font-semibold leading-none">{user?.name || 'User'}</span>
                </div>
                <div
                  className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-xs"
                  aria-hidden="true"
                >
                  {getInitials(user?.name || 'U')}
                </div>
                <ChevronDown
                  className={cn(
                    'h-4 w-4 text-muted-foreground transition-transform mr-1',
                    userMenuOpen && 'transform rotate-180'
                  )}
                  aria-hidden="true"
                />
                <span className="sr-only">User menu</span>
              </button>

              <AnimatePresence>
                {userMenuOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    transition={{ duration: 0.2 }}
                    className="absolute right-0 top-full mt-2 w-56 rounded-xl border bg-popover p-1 shadow-lg text-popover-foreground outline-none"
                    role="menu"
                    aria-labelledby="user-menu-button"
                    aria-orientation="vertical"
                  >
                    <div className="px-2 py-1.5 text-sm font-semibold text-foreground/50 border-b mb-1" role="none">
                      My Account
                    </div>
                    <Link
                      href="/profile"
                      className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                      onClick={() => setUserMenuOpen(false)}
                      role="menuitem"
                      tabIndex={0}
                    >
                      <User className="mr-2 h-4 w-4" aria-hidden="true" />
                      <span>Profile</span>
                    </Link>
                    <Link
                      href="/settings"
                      className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                      onClick={() => setUserMenuOpen(false)}
                      role="menuitem"
                      tabIndex={0}
                    >
                      <Settings className="mr-2 h-4 w-4" aria-hidden="true" />
                      <span>Settings</span>
                    </Link>
                    <div className="h-px bg-border my-1" role="none" />
                    <button
                      onClick={() => {
                        logout();
                        setUserMenuOpen(false);
                      }}
                      className="relative flex w-full cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-destructive/10 hover:text-destructive data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                      role="menuitem"
                      tabIndex={0}
                    >
                      <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />
                      <span>Log out</span>
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : (
            !isLoading && (
              <>
                <Link
                  href="/login"
                  className="text-sm font-semibold leading-6 text-foreground hover:text-primary transition-colors"
                >
                  Log in
                </Link>
                <Button
                  asChild
                  className="rounded-full px-6 bg-gradient-to-r from-primary to-secondary hover:opacity-90 transition-opacity"
                >
                  <Link href="/register">Get Started</Link>
                </Button>
              </>
            )
          )}
        </div>
      </nav>

      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, x: '100%' }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: '100%' }}
            transition={{ type: 'tween', ease: 'easeOut', duration: 0.3 }}
            className="fixed inset-0 z-50 lg:hidden"
          >
            <div
              className="fixed inset-0 bg-background/80 backdrop-blur-sm"
              onClick={() => setMobileMenuOpen(false)}
              aria-hidden="true"
            />
            <div
              id="mobile-menu"
              className="fixed inset-y-0 right-0 z-50 w-full overflow-y-auto bg-background px-6 py-6 sm:max-w-sm sm:ring-1 sm:ring-foreground/10 shadow-2xl"
              role="dialog"
              aria-modal="true"
              aria-labelledby="mobile-menu-title"
            >
              <div className="flex items-center justify-between">
                <Link
                  href="/"
                  className="-m-1.5 p-1.5 flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label="Soul Sense Home"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <div className="rounded-xl bg-gradient-to-br from-primary to-secondary p-2 shadow-md text-white">
                    <BookOpen className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <span className="text-xl font-bold" id="mobile-menu-title">
                    Soul Sense
                  </span>
                </Link>
                <button
                  type="button"
                  className="-m-2.5 rounded-md p-2.5 text-foreground hover:bg-accent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  onClick={() => setMobileMenuOpen(false)}
                  aria-label="Close menu"
                >
                  <X className="h-6 w-6" aria-hidden="true" />
                </button>
              </div>
              <div className="mt-6 flow-root">
                <div className="-my-6 divide-y divide-foreground/10" role="none">
                  <div className="space-y-2 py-6" role="menu">
                    {navLinks.map((item) => {
                      const Icon = item.icon;
                      const isActive = pathname === item.href;
                      return (
                        <Link
                          key={item.name}
                          href={item.href}
                          className={cn(
                            '-mx-3 flex items-center gap-3 rounded-lg px-3 py-2 text-base font-semibold leading-7 transition-all',
                            isActive
                              ? 'bg-primary/10 text-primary'
                              : 'text-foreground hover:bg-accent'
                          )}
                          onClick={() => setMobileMenuOpen(false)}
                          role="menuitem"
                          aria-current={isActive ? 'page' : undefined}
                        >
                          {Icon && <Icon className="h-5 w-5" aria-hidden="true" />}
                          <span>{item.name}</span>
                        </Link>
                      );
                    })}
                  </div>
                  <div className="py-6 flex flex-col gap-4">
                    {isAuthenticated ? (
                      <div className="space-y-3">
                        <div className="flex items-center gap-3 px-3 py-2 border-b border-foreground/10 pb-4 mb-2">
                          <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm">
                            {getInitials(user?.name || 'U')}
                          </div>
                          <div className="flex flex-col">
                            <span className="font-semibold">{user?.name}</span>
                            <span className="text-xs text-muted-foreground">Logged in</span>
                          </div>
                        </div>
                        <Link
                          href="/profile"
                          className="-mx-3 flex items-center gap-3 rounded-lg px-3 py-2 text-base font-semibold leading-7 text-foreground hover:bg-accent"
                          onClick={() => setMobileMenuOpen(false)}
                        >
                          <User className="h-5 w-5" />
                          Profile
                        </Link>
                        <Link
                          href="/settings"
                          className="-mx-3 flex items-center gap-3 rounded-lg px-3 py-2 text-base font-semibold leading-7 text-foreground hover:bg-accent"
                          onClick={() => setMobileMenuOpen(false)}
                        >
                          <Settings className="h-5 w-5" />
                          Settings
                        </Link>
                        <Button
                          variant="ghost"
                          className="justify-start -mx-3 px-3 py-2.5 text-base font-semibold leading-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                          onClick={() => {
                            logout();
                            setMobileMenuOpen(false);
                          }}
                        >
                          <LogOut className="h-5 w-5 mr-3" />
                          Logout
                        </Button>
                      </div>
                    ) : (
                      <>
                        <Link
                          href="/login"
                          className="-mx-3 block rounded-lg px-3 py-2.5 text-base font-semibold leading-7 text-foreground hover:bg-accent transition-all"
                          onClick={() => setMobileMenuOpen(false)}
                        >
                          Log in
                        </Link>
                        <Button
                          className="w-full rounded-full bg-gradient-to-r from-primary to-secondary"
                          asChild
                        >
                          <Link href="/register" onClick={() => setMobileMenuOpen(false)}>
                            Get Started
                          </Link>
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
