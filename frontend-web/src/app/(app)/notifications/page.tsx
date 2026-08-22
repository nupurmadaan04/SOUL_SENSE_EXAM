'use client';

import * as React from 'react';
import {
  Bell,
  CheckCheck,
  Trash2,
  Sparkles,
  ClipboardList,
  BookOpen,
  ShieldCheck,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';
import { useRouter } from 'next/navigation';
import { toast } from '@/lib/toast';

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  time: string;
  unread: boolean;
  type: 'exam' | 'journal' | 'profile' | 'system';
  href?: string;
}

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
    message: 'Take 2 minutes to reflect and log your daily emotional wellbeing in your journal.',
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

export default function NotificationsPage() {
  const router = useRouter();
  const [filter, setFilter] = React.useState<'all' | 'unread'>('all');
  const [notifications, setNotifications] = React.useState<NotificationItem[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('soulsense_notifications');
        if (saved) return JSON.parse(saved);
      } catch (e) {}
    }
    return DEFAULT_NOTIFICATIONS;
  });

  React.useEffect(() => {
    try {
      localStorage.setItem('soulsense_notifications', JSON.stringify(notifications));
    } catch (e) {}
  }, [notifications]);

  const handleMarkAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })));
    toast.success('All notifications marked as read');
  };

  const handleClearAll = () => {
    setNotifications([]);
    toast.info('All notifications cleared');
  };

  const handleResetDefaults = () => {
    setNotifications(DEFAULT_NOTIFICATIONS);
    toast.success('Restored sample notifications');
  };

  const handleItemClick = (item: NotificationItem) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === item.id ? { ...n, unread: false } : n))
    );
    if (item.href) {
      router.push(item.href);
    }
  };

  const unreadCount = notifications.filter((n) => n.unread).length;
  const filteredNotifications = notifications.filter((n) => (filter === 'unread' ? n.unread : true));

  const getNotifIcon = (type: NotificationItem['type']) => {
    switch (type) {
      case 'exam':
        return <ClipboardList className="h-5 w-5 text-primary" />;
      case 'journal':
        return <BookOpen className="h-5 w-5 text-amber-500" />;
      case 'system':
        return <ShieldCheck className="h-5 w-5 text-emerald-500" />;
      default:
        return <Sparkles className="h-5 w-5 text-primary" />;
    }
  };

  return (
    <div className="p-4 md:p-10 space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-border/40 pb-6">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-2xl bg-primary/10 text-primary">
              <Bell className="h-6 w-6" />
            </div>
            <h1 className="text-3xl font-black tracking-tight text-foreground">Notifications</h1>
          </div>
          <p className="text-muted-foreground text-sm">
            Stay updated with your personalized assessment schedules and mental wellbeing alerts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <Button
              onClick={handleMarkAllRead}
              variant="outline"
              size="sm"
              className="rounded-xl text-xs font-bold gap-2"
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Mark all as read
            </Button>
          )}
          {notifications.length > 0 ? (
            <Button
              onClick={handleClearAll}
              variant="outline"
              size="sm"
              className="rounded-xl text-xs font-bold text-destructive hover:bg-destructive/10 gap-2 border-border/60"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear all
            </Button>
          ) : (
            <Button
              onClick={handleResetDefaults}
              variant="outline"
              size="sm"
              className="rounded-xl text-xs font-bold gap-2"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Reset Demo
            </Button>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setFilter('all')}
          className={cn(
            'px-4 py-2 rounded-xl text-xs font-bold transition-all',
            filter === 'all'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'bg-card text-muted-foreground hover:text-foreground border border-border/60'
          )}
        >
          All ({notifications.length})
        </button>
        <button
          onClick={() => setFilter('unread')}
          className={cn(
            'px-4 py-2 rounded-xl text-xs font-bold transition-all',
            filter === 'unread'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'bg-card text-muted-foreground hover:text-foreground border border-border/60'
          )}
        >
          Unread ({unreadCount})
        </button>
      </div>

      {/* Notification List */}
      <div className="rounded-3xl border border-border/80 bg-card/90 backdrop-blur-xl shadow-xl overflow-hidden divide-y divide-border/30">
        {filteredNotifications.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <Bell className="h-10 w-10 text-muted-foreground/30 mx-auto" />
            <h3 className="text-base font-bold text-foreground">
              {filter === 'unread' ? 'No unread notifications' : 'No notifications'}
            </h3>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto">
              You are completely caught up! We will alert you whenever new assessment questions or daily mindfulness milestones are ready.
            </p>
          </div>
        ) : (
          filteredNotifications.map((item) => (
            <div
              key={item.id}
              onClick={() => handleItemClick(item)}
              className={cn(
                'p-5 transition-all hover:bg-muted/40 cursor-pointer flex items-start gap-4 group relative',
                item.unread ? 'bg-primary/5' : 'bg-transparent'
              )}
            >
              <div className="p-2.5 rounded-2xl bg-card border border-border/60 shadow-sm shrink-0">
                {getNotifIcon(item.type)}
              </div>

              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <p className={cn('text-sm font-bold', item.unread ? 'text-foreground' : 'text-foreground/80')}>
                      {item.title}
                    </p>
                    {item.unread && (
                      <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-bold">
                        New
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground shrink-0">{item.time}</span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {item.message}
                </p>
              </div>

              {item.href && (
                <div className="shrink-0 self-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <ArrowRight className="h-4 w-4 text-primary" />
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
