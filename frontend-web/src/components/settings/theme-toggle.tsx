'use client';

import * as React from 'react';
import { Sun, Moon, Laptop } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from 'next-themes';
import { cn } from '../../lib/utils';

// ─── Types ───────────────────────────────────────────────────────────────────

export type ThemeValue = 'light' | 'dark' | 'system';

export interface ThemeToggleProps {
  /** Currently active theme preference */
  value?: ThemeValue;
  /** Callback invoked with the newly selected theme */
  onChange?: (value: ThemeValue) => void;
  /** Optional extra class names on the root element */
  className?: string;
}

const STORAGE_KEY = 'theme';

// ─── Constants ────────────────────────────────────────────────────────────────

const OPTIONS: {
  value: ThemeValue;
  label: string;
  Icon: React.ElementType;
  iconLabel: string;
}[] = [
  { value: 'light', label: 'Light', Icon: Sun, iconLabel: 'Sun icon' },
  { value: 'dark', label: 'Dark', Icon: Moon, iconLabel: 'Moon icon' },
  { value: 'system', label: 'System', Icon: Laptop, iconLabel: 'Laptop icon' },
];

/**
 * ThemeToggle
 *
 * A fully animated segmented control that lets the user pick between Light,
 * Dark, and System colour schemes with immediate synchronous updates.
 */
export function ThemeToggle({ value, onChange, className }: ThemeToggleProps) {
  const scopeId = React.useId();
  const [mounted, setMounted] = React.useState(false);
  const [systemTheme, setSystemTheme] = React.useState<'light' | 'dark'>('light');
  const { theme: activeTheme, setTheme } = useTheme();

  // Local state initialized with prop or activeTheme
  const currentThemeValue = (value || activeTheme || 'system') as ThemeValue;
  const [selectedTheme, setSelectedTheme] = React.useState<ThemeValue>(currentThemeValue);

  React.useEffect(() => {
    if (value) {
      setSelectedTheme(value);
    }
  }, [value]);

  // Avoid hydration mismatch and track system theme
  React.useEffect(() => {
    setMounted(true);

    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const updateSystemTheme = () => setSystemTheme(mq.matches ? 'dark' : 'light');

    updateSystemTheme();
    mq.addEventListener('change', updateSystemTheme);
    return () => mq.removeEventListener('change', updateSystemTheme);
  }, []);

  const handleSelectTheme = (newTheme: ThemeValue) => {
    setSelectedTheme(newTheme);
    
    // 1. Immediately call next-themes setTheme
    setTheme(newTheme);

    // 2. Direct instant DOM class update to ensure entire UI transitions instantly
    if (typeof document !== 'undefined') {
      const isDark =
        newTheme === 'dark' ||
        (newTheme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

      if (isDark) {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
      } else {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
      }
    }

    // 3. Immediately persist to localStorage
    try {
      localStorage.setItem(STORAGE_KEY, newTheme);
    } catch (e) {
      // Fail silently if localStorage is blocked
    }

    // 4. Notify parent callback
    onChange?.(newTheme);
  };

  if (!mounted) {
    return (
      <div className={cn('space-y-5 animate-pulse', className)}>
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-muted" />
          <div className="space-y-2">
            <div className="h-4 w-24 bg-muted rounded" />
            <div className="h-3 w-32 bg-muted rounded" />
          </div>
        </div>
        <div className="h-10 w-full bg-muted rounded-xl" />
      </div>
    );
  }

  const resolvedTheme = selectedTheme === 'system' ? systemTheme : selectedTheme;
  const activeOption = OPTIONS.find((o) => o.value === selectedTheme) ?? OPTIONS[2];

  return (
    <div className={cn('space-y-5', className)}>
      {/* ── Section header ── */}
      <div className="flex items-center gap-3">
        <motion.div
          key={resolvedTheme}
          initial={{ rotate: -30, opacity: 0, scale: 0.7 }}
          animate={{ rotate: 0, opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 18 }}
          className="p-2.5 rounded-xl bg-primary/10 text-primary shrink-0"
          aria-hidden="true"
        >
          {resolvedTheme === 'dark' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
        </motion.div>
        <div>
          <h3 className="text-sm font-semibold leading-none tracking-tight">Appearance</h3>
          <p className="text-xs text-muted-foreground mt-1">Choose your preferred colour scheme</p>
        </div>
      </div>

      {/* ── Segmented control ── */}
      <div
        role="radiogroup"
        aria-label="Theme selection"
        className={cn(
          'relative flex items-center gap-1 p-1 rounded-xl',
          'bg-muted/60 border border-border/60',
          'backdrop-blur-sm'
        )}
      >
        {OPTIONS.map((option) => {
          const isActive = selectedTheme === option.value;
          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={isActive}
              id={`${scopeId}-theme-option-${option.value}`}
              onClick={() => handleSelectTheme(option.value)}
              className={cn(
                'relative z-10 flex flex-1 items-center justify-center gap-2',
                'py-2.5 px-3 rounded-lg text-xs font-semibold',
                'transition-all duration-200 focus-visible:outline-none',
                'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 cursor-pointer',
                isActive
                  ? 'bg-card text-foreground shadow-sm border border-border/60'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
              )}
            >
              <option.Icon
                className={cn(
                  'h-3.5 w-3.5 shrink-0 transition-all duration-300',
                  isActive && option.value === 'light' && 'text-amber-500',
                  isActive && option.value === 'dark' && 'text-indigo-400',
                  isActive && option.value === 'system' && 'text-primary'
                )}
                aria-label={option.iconLabel}
              />
              <span>{option.label}</span>
            </button>
          );
        })}
      </div>

      {/* ── Current theme label ── */}
      <motion.p
        key={selectedTheme}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="text-[11px] text-muted-foreground text-center"
      >
        {selectedTheme === 'system'
          ? `Following system preference · currently ${resolvedTheme}`
          : `${activeOption.label} mode active`}
      </motion.p>
    </div>
  );
}

/**
 * Helper to initialize the theme from localStorage on application start.
 */
export function initTheme(): ThemeValue {
  if (typeof window === 'undefined') return 'system';
  try {
    const saved = localStorage.getItem(STORAGE_KEY) as ThemeValue | null;
    const preference: ThemeValue =
      saved && ['light', 'dark', 'system'].includes(saved) ? saved : 'system';

    return preference;
  } catch {
    return 'system';
  }
}
