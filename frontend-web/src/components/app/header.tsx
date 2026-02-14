'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bell, LogOut, Settings, User } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';

interface HeaderProps {
  className?: string;
  notificationCount?: number;
}

export const Header = React.forwardRef<HTMLHeaderElement, HeaderProps>(
  ({ className, notificationCount = 0 }, ref) => {
    const router = useRouter();
    const { user, logout } = useAuth();
    const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);
    const dropdownRef = React.useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    React.useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
          setIsDropdownOpen(false);
        }
      };

      if (isDropdownOpen) {
        document.addEventListener('mousedown', handleClickOutside);
      }

      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }, [isDropdownOpen]);

    // Get user initials from name
    const getUserInitials = (name?: string) => {
      if (!name) return 'U';
      const trimmedName = name.trim();
      if (!trimmedName) return 'U';

      // Split on any whitespace and ignore empty segments
      const parts = trimmedName.split(/\s+/);

      if (parts.length >= 2 && parts[0] && parts[1]) {
        return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
      }

      return trimmedName.slice(0, 2).toUpperCase();
    };

    const handleLogout = async () => {
      setIsDropdownOpen(false);
      await logout();
    };

    const handleNavigate = (path: string) => {
      setIsDropdownOpen(false);
      router.push(path);
    };

    return (
      <header
        ref={ref}
        className={cn(
          'sticky top-0 z-50 w-full border-b border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-950',
          className
        )}
      >
        <div className="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Left side - Logo/App name */}
          <Link
            href="/dashboard"
            className="flex items-center gap-2 text-lg font-semibold text-gray-900 transition-colors hover:text-blue-600 dark:text-white dark:hover:text-blue-400"
          >
            {/* You can replace this with an actual logo image */}
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white font-bold">
              S
            </div>
            <span className="hidden sm:inline">SoulSense</span>
          </Link>

          {/* Right side - Notifications and User menu */}
          <div className="flex items-center gap-4">
            {/* Notifications Icon */}
            <button
              onClick={() => handleNavigate('/notifications')}
              className="relative rounded-lg p-2 text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white"
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5" />
              {notificationCount > 0 && (
                <span className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-semibold text-white">
                  {notificationCount > 99 ? '99+' : notificationCount}
                </span>
              )}
            </button>

            {/* User Avatar Dropdown */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="flex items-center gap-2 rounded-lg p-1 transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
                aria-label="User menu"
                aria-expanded={isDropdownOpen}
              >
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-blue-600 text-sm font-semibold text-white">
                    {getUserInitials(user?.name)}
                  </AvatarFallback>
                </Avatar>
              </button>

              {/* Dropdown Menu */}
              {isDropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 rounded-lg border border-gray-200 bg-white shadow-lg z-50 dark:border-gray-700 dark:bg-gray-900">
                  {/* User Info */}
                  <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">
                      {user?.name || 'User'}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{user?.email}</p>
                  </div>

                  {/* Menu Items */}
                  <div className="space-y-1 py-2">
                    <button
                      onClick={() => handleNavigate('/profile')}
                      className="flex w-full items-center gap-3 px-4 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    >
                      <User className="h-4 w-4" />
                      Profile
                    </button>

                    <button
                      onClick={() => handleNavigate('/settings')}
                      className="flex w-full items-center gap-3 px-4 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    >
                      <Settings className="h-4 w-4" />
                      Settings
                    </button>
                  </div>

                  {/* Logout */}
                  <div className="border-t border-gray-200 py-2 dark:border-gray-700">
                    <button
                      onClick={handleLogout}
                      className="flex w-full items-center gap-3 px-4 py-2 text-sm text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-gray-800"
                    >
                      <LogOut className="h-4 w-4" />
                      Logout
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>
    );
  }
);

Header.displayName = 'Header';
