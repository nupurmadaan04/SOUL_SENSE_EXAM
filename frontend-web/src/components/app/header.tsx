'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Bell,
  LogOut,
  Settings,
  User,
  Search,
  ChevronDown,
  CheckCheck,
  Trash2,
  Sparkles,
  ClipboardList,
  BookOpen,
  ShieldCheck,
  ExternalLink,
  Activity,
  Heart,
  TrendingUp,
  HelpCircle,
  X
} from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage, Button, Input } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { SyncButton } from '@/components/offline';
import { toast } from '@/lib/toast';

interface HeaderProps {
  className?: string;
}

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  time: string;
  unread: boolean;
  type: 'exam' | 'journal' | 'profile' | 'system';
  href?: string;
}

interface SearchItem {
  title: string;
  category: string;
  href: string;
  icon: React.ElementType;
}

const SEARCH_ITEMS: SearchItem[] = [
  { title: 'Take EQ Assessment', category: 'Assessments', href: '/exam', icon: ClipboardList },
  { title: 'Personalized Custom Assessment', category: 'Assessments', href: '/dashboard', icon: Sparkles },
  { title: 'Write Journal Reflection', category: 'Journal', href: '/journal', icon: BookOpen },
  { title: 'Daily Mood Check-in', category: 'Journal', href: '/dashboard', icon: Heart },
  { title: 'Assessment Results & History', category: 'Analytics', href: '/results', icon: TrendingUp },
  { title: 'Emotional Trend Graph', category: 'Analytics', href: '/dashboard', icon: Activity },
  { title: 'Health & Emotional Profile', category: 'Settings', href: '/profile', icon: User },
  { title: 'Privacy & Security Settings', category: 'Settings', href: '/settings#privacy', icon: ShieldCheck },
  { title: 'Help & Support Guide', category: 'Settings', href: '/settings#support', icon: HelpCircle },
];

const DEFAULT_NOTIFICATIONS: NotificationItem[] = [
  {
    id: 'notif-1',
    title: 'Personalized Assessment Active',
    message: 'Questions have been tailored according to your health & emotional profile.',
    time: 'Just now',
    unread: true,
    type: 'exam',
    href: '/exam',
  },
  {
    id: 'notif-2',
    title: 'Daily Mindfulness Check-in',
    message: 'Take 2 minutes to reflect and log your daily emotional wellbeing.',
    time: '2 hours ago',
    unread: true,
    type: 'journal',
    href: '/journal',
  },
  {
    id: 'notif-3',
    title: 'Data & Privacy Secured',
    message: 'All your psychological logs are encrypted with multi-layer security.',
    time: '1 day ago',
    unread: false,
    type: 'system',
    href: '/settings#privacy',
  },
];

export const Header = React.forwardRef<HTMLElement, HeaderProps>(({ className }, ref) => {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);
  const [isNotifOpen, setIsNotifOpen] = React.useState(false);
  const [isScrolled, setIsScrolled] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [isSearchOpen, setIsSearchOpen] = React.useState(false);

  const [notifications, setNotifications] = React.useState<NotificationItem[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('soulsense_notifications');
        if (saved) return JSON.parse(saved);
      } catch (e) {}
    }
    return DEFAULT_NOTIFICATIONS;
  });

  const dropdownRef = React.useRef<HTMLDivElement>(null);
  const notifRef = React.useRef<HTMLDivElement>(null);
  const searchRef = React.useRef<HTMLDivElement>(null);

  // Sync notifications to localStorage
  React.useEffect(() => {
    try {
      localStorage.setItem('soulsense_notifications', JSON.stringify(notifications));
    } catch (e) {}
  }, [notifications]);

  // Track scroll for header transition
  React.useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close dropdowns on outside click
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setIsNotifOpen(false);
      }
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const unreadCount = notifications.filter((n) => n.unread).length;

  const handleMarkAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })));
    toast.success('All notifications marked as read');
  };

  const handleClearAll = () => {
    setNotifications([]);
    toast.info('Notifications cleared');
  };

  const handleNotificationClick = (item: NotificationItem) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === item.id ? { ...n, unread: false } : n))
    );
    setIsNotifOpen(false);
    if (item.href) {
      router.push(item.href);
    }
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

  const handleLogout = async () => {
    setIsDropdownOpen(false);
    await logout();
  };

  const handleNavigate = (path: string) => {
    setIsDropdownOpen(false);
    setIsNotifOpen(false);
    setIsSearchOpen(false);
    router.push(path);
  };

  const filteredSearchResults = SEARCH_ITEMS.filter((item) =>
    item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <header
      ref={ref}
      className={cn(
        'sticky top-0 z-40 w-full transition-all duration-300 flex items-center',
        isScrolled
          ? 'h-16 bg-background/85 backdrop-blur-2xl border-b border-border/40 shadow-sm'
          : 'h-16 bg-background/50 backdrop-blur-md border-b border-border/20',
        className
      )}
    >
      <div className="flex h-full items-center justify-between px-4 sm:px-6 lg:px-8 w-full max-w-[1600px] mx-auto gap-4">
        {/* Mobile Brand Logo */}
        <div className="flex md:hidden items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary text-white font-bold text-sm shadow-md">
            <BookOpen className="w-5 h-5" />
          </div>
          <span className="font-bold text-foreground text-sm tracking-tight">Soul Sense</span>
        </div>

        {/* Search Bar with Interactive Palette */}
        <div className="flex-1 max-w-md hidden md:block relative" ref={searchRef}>
          <div className="relative group flex items-center">
            <Search className="absolute left-3.5 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors z-10 pointer-events-none" />
            <Input
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setIsSearchOpen(true);
              }}
              onFocus={() => setIsSearchOpen(true)}
              placeholder="Search emotions, exams, or journals..."
              className="pl-10 pr-8 h-10 bg-card/80 border border-border/80 text-foreground placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:border-primary rounded-full shadow-xs transition-all w-full text-xs font-medium"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Interactive Search Dropdown */}
          <AnimatePresence>
            {isSearchOpen && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 6 }}
                className="absolute left-0 top-12 w-full bg-popover border border-border/80 rounded-2xl shadow-xl z-50 overflow-hidden"
              >
                <div className="p-2 divide-y divide-border/30 max-h-72 overflow-y-auto">
                  {filteredSearchResults.length > 0 ? (
                    filteredSearchResults.map((item, idx) => {
                      const Icon = item.icon;
                      return (
                        <button
                          key={idx}
                          onClick={() => handleNavigate(item.href)}
                          className="w-full p-2.5 rounded-xl hover:bg-muted/50 transition-colors flex items-center justify-between text-left cursor-pointer group"
                        >
                          <div className="flex items-center gap-2.5">
                            <div className="p-1.5 rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                              <Icon className="h-4 w-4" />
                            </div>
                            <div>
                              <p className="text-xs font-bold text-foreground">{item.title}</p>
                              <span className="text-[10px] text-muted-foreground">{item.category}</span>
                            </div>
                          </div>
                        </button>
                      );
                    })
                  ) : (
                    <div className="p-4 text-center text-xs text-muted-foreground">
                      No results found for &ldquo;{searchQuery}&rdquo;
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right side - Sync, Notifications and User Menu */}
        <div className="flex items-center gap-2 sm:gap-3 ml-auto">
          <SyncButton />

          {/* NOTIFICATION BELL & DROPDOWN */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setIsNotifOpen(!isNotifOpen)}
              className={cn(
                'relative p-2 rounded-full border border-border/80 bg-card/80 text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors shadow-xs cursor-pointer',
                isNotifOpen && 'bg-muted text-foreground'
              )}
              title="Notifications"
            >
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <span className="absolute top-0.5 right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-primary-foreground shadow-xs animate-pulse">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* Notification Dropdown */}
            <AnimatePresence>
              {isNotifOpen && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: 8 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: 8 }}
                  className="absolute right-0 top-12 w-80 sm:w-96 rounded-2xl border border-border/80 bg-popover shadow-2xl z-50 overflow-hidden"
                >
                  <div className="p-4 border-b border-border/40 flex items-center justify-between bg-muted/20">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-bold text-foreground">Notifications</h4>
                      {unreadCount > 0 && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-primary/20 text-primary">
                          {unreadCount} new
                        </span>
                      )}
                    </div>
                    {notifications.length > 0 && (
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleMarkAllAsRead}
                          className="h-7 px-2 text-[10px] text-muted-foreground hover:text-foreground"
                          title="Mark all as read"
                        >
                          <CheckCheck className="h-3.5 w-3.5 mr-1" />
                          Read All
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleClearAll}
                          className="h-7 px-2 text-[10px] text-destructive hover:text-destructive/80"
                          title="Clear all"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    )}
                  </div>

                  <div className="divide-y divide-border/30 max-h-72 overflow-y-auto">
                    {notifications.length > 0 ? (
                      notifications.map((item) => (
                        <div
                          key={item.id}
                          onClick={() => handleNotificationClick(item)}
                          className={cn(
                            'p-3.5 transition-colors cursor-pointer hover:bg-muted/40 flex items-start gap-3',
                            item.unread && 'bg-primary/5'
                          )}
                        >
                          <div className="p-2 rounded-xl bg-primary/10 text-primary shrink-0 mt-0.5">
                            <Sparkles className="h-3.5 w-3.5" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-1">
                              <p className={cn('text-xs font-bold truncate', item.unread ? 'text-foreground' : 'text-muted-foreground')}>
                                {item.title}
                              </p>
                              <span className="text-[9px] text-muted-foreground shrink-0">{item.time}</span>
                            </div>
                            <p className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5">
                              {item.message}
                            </p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="p-6 text-center text-xs text-muted-foreground">
                        No notifications yet
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* USER AVATAR & DROPDOWN */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex items-center gap-2 p-1.5 rounded-full border border-border/80 bg-card/80 hover:bg-muted/50 transition-colors cursor-pointer shadow-xs"
            >
              <Avatar className="h-7 w-7 border border-background shadow-xs">
                <AvatarFallback className="bg-gradient-to-br from-primary to-primary/70 text-white text-[10px] font-bold">
                  {getUserInitials(user?.name || user?.username)}
                </AvatarFallback>
              </Avatar>
              <span className="text-xs font-bold text-foreground hidden sm:inline max-w-[100px] truncate">
                {user?.name?.split(' ')[0] || user?.username || 'Account'}
              </span>
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </button>

            {/* Dropdown Menu */}
            <AnimatePresence>
              {isDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: 8 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: 8 }}
                  className="absolute right-0 top-12 w-52 rounded-2xl border border-border/80 bg-popover shadow-2xl z-50 p-2 space-y-1"
                >
                  <div className="px-3 py-2 border-b border-border/40">
                    <p className="text-xs font-bold text-foreground truncate">{user?.name || user?.username}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{user?.email}</p>
                  </div>

                  <button
                    onClick={() => handleNavigate('/profile')}
                    className="w-full px-3 py-2 rounded-xl text-xs font-semibold text-foreground hover:bg-muted/50 flex items-center gap-2 cursor-pointer"
                  >
                    <User className="h-3.5 w-3.5 text-primary" />
                    <span>My Profile</span>
                  </button>

                  <button
                    onClick={() => handleNavigate('/settings')}
                    className="w-full px-3 py-2 rounded-xl text-xs font-semibold text-foreground hover:bg-muted/50 flex items-center gap-2 cursor-pointer"
                  >
                    <Settings className="h-3.5 w-3.5 text-primary" />
                    <span>Settings</span>
                  </button>

                  <button
                    onClick={() => handleNavigate('/settings#support')}
                    className="w-full px-3 py-2 rounded-xl text-xs font-semibold text-foreground hover:bg-muted/50 flex items-center gap-2 cursor-pointer"
                  >
                    <HelpCircle className="h-3.5 w-3.5 text-primary" />
                    <span>Help & FAQs</span>
                  </button>

                  <div className="pt-1 border-t border-border/40">
                    <button
                      onClick={handleLogout}
                      className="w-full px-3 py-2 rounded-xl text-xs font-semibold text-destructive hover:bg-destructive/10 flex items-center gap-2 cursor-pointer"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      <span>Log Out</span>
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </header>
  );
});

Header.displayName = 'Header';
