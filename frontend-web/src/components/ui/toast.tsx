'use client';

import * as React from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { cn, generateId } from '@/lib/utils';

export type ToastType = 'success' | 'error' | 'warning' | 'info';
export type ToastPosition = 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';

export interface ToastOptions {
  id?: string;
  type: ToastType;
  message: string;
  duration?: number;
  title?: string;
}

export interface ToastItem extends ToastOptions {
  id: string;
}

interface ToastContextValue {
  toasts: ToastItem[];
  toast: (options: ToastOptions) => string;
  dismiss: (id: string) => void;
  clear: () => void;
  position: ToastPosition;
}

const ToastContext = React.createContext<ToastContextValue | undefined>(undefined);

const typeStyles: Record<ToastType, string> = {
  success: 'border-emerald-500/60 bg-emerald-50 text-emerald-900',
  error: 'border-red-500/60 bg-red-50 text-red-900',
  warning: 'border-amber-500/60 bg-amber-50 text-amber-900',
  info: 'border-sky-500/60 bg-sky-50 text-sky-900',
};

const positionStyles: Record<ToastPosition, string> = {
  'top-right': 'top-4 right-4 items-end',
  'top-left': 'top-4 left-4 items-start',
  'bottom-right': 'bottom-4 right-4 items-end',
  'bottom-left': 'bottom-4 left-4 items-start',
};

const stackDirection: Record<ToastPosition, string> = {
  'top-right': 'flex-col',
  'top-left': 'flex-col',
  'bottom-right': 'flex-col-reverse',
  'bottom-left': 'flex-col-reverse',
};

export interface ToastProviderProps {
  children: React.ReactNode;
  position?: ToastPosition;
  defaultDuration?: number;
}

const DEFAULT_DURATION = 5000;

export function ToastProvider({
  children,
  position = 'top-right',
  defaultDuration = DEFAULT_DURATION,
}: ToastProviderProps) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);
  const [mounted, setMounted] = React.useState(false);
  const timeoutsRef = React.useRef(new Map<string, ReturnType<typeof setTimeout>>());

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const dismiss = React.useCallback((id: string) => {
    setToasts((prev: ToastItem[]) => prev.filter((toastItem: ToastItem) => toastItem.id !== id));
    const timeout = timeoutsRef.current.get(id);
    if (timeout) {
      clearTimeout(timeout);
      timeoutsRef.current.delete(id);
    }
  }, []);

  const clear = React.useCallback(() => {
    setToasts([]);
    timeoutsRef.current.forEach((timeout: ReturnType<typeof setTimeout>) => clearTimeout(timeout));
    timeoutsRef.current.clear();
  }, []);

  const toast = React.useCallback(
    (options: ToastOptions) => {
      const id = options.id ?? generateId('toast');
      const duration = options.duration ?? defaultDuration;
      const nextToast: ToastItem = {
        ...options,
        id,
      };

      setToasts((prev: ToastItem[]) => [nextToast, ...prev]);

      if (duration > 0) {
        const timeout = setTimeout(() => dismiss(id), duration);
        timeoutsRef.current.set(id, timeout);
      }

      return id;
    },
    [defaultDuration, dismiss]
  );

  React.useEffect(() => {
    return () => {
      timeoutsRef.current.forEach((timeout: ReturnType<typeof setTimeout>) => clearTimeout(timeout));
      timeoutsRef.current.clear();
    };
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, toast, dismiss, clear, position }}>
      {children}
      {mounted
        ? createPortal(
            <div
              className={cn(
                'fixed z-50 flex w-full max-w-sm gap-3 p-4 pointer-events-none',
                positionStyles[position],
                stackDirection[position]
              )}
              aria-live="polite"
              aria-atomic="false"
            >
              {toasts.map((toastItem: ToastItem) => (
                <div
                  key={toastItem.id}
                  className={cn(
                    'pointer-events-auto w-full rounded-lg border shadow-lg',
                    typeStyles[toastItem.type]
                  )}
                  role={toastItem.type === 'error' ? 'alert' : 'status'}
                >
                  <div className="flex items-start justify-between gap-3 p-4">
                    <div className="flex-1">
                      {toastItem.title ? (
                        <p className="text-sm font-semibold">{toastItem.title}</p>
                      ) : null}
                      <p className={cn('text-sm leading-snug', toastItem.title ? 'mt-1' : '')}>
                        {toastItem.message}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => dismiss(toastItem.id)}
                      className="rounded-md p-1 text-current/70 transition hover:text-current focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      aria-label="Dismiss notification"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>,
            document.body
          )
        : null}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider.');
  }

  return context;
}
