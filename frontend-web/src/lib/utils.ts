/**
 * Utility Functions for TailwindCSS and React Components
 * ======================================================
 * This file provides utility functions for class name management and common patterns.
 */

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Combines class names using clsx and optimizes Tailwind classes with twMerge.
 * This is the primary utility for composing class names in components.
 *
 * @example
 * cn('px-4 py-2', isActive && 'bg-primary', className)
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/**
 * Type for variant configuration used in component styling.
 */
export type VariantProps<T extends (...args: unknown[]) => unknown> = Parameters<T>[0];

/**
 * Creates a variant-based class generator for components.
 * Simplified version of class-variance-authority for basic use cases.
 *
 * @example
 * const buttonVariants = createVariants({
 *   base: 'inline-flex items-center justify-center rounded-md',
 *   variants: {
 *     variant: {
 *       primary: 'bg-primary text-primary-foreground',
 *       secondary: 'bg-secondary text-secondary-foreground',
 *     },
 *     size: {
 *       sm: 'h-9 px-3 text-sm',
 *       md: 'h-10 px-4 text-base',
 *       lg: 'h-11 px-8 text-lg',
 *     },
 *   },
 *   defaultVariants: {
 *     variant: 'primary',
 *     size: 'md',
 *   },
 * });
 */
export function createVariants<
    T extends {
        base?: string;
        variants: Record<string, Record<string, string>>;
        defaultVariants?: Record<string, string>;
    },
>(config: T) {
    return function getVariantClasses(
        props?: Partial<{
            [K in keyof T['variants']]: keyof T['variants'][K];
        }> & { className?: string }
    ): string {
        const { className, ...variantProps } = props || {};
        const classes: string[] = [];

        // Add base classes
        if (config.base) {
            classes.push(config.base);
        }

        // Add variant classes
        for (const [key, variants] of Object.entries(config.variants)) {
            const variantKey = (variantProps as Record<string, string | undefined>)?.[key];
            const defaultVariant = config.defaultVariants?.[key];
            const selectedVariant = variantKey || defaultVariant;

            if (selectedVariant && variants[selectedVariant]) {
                classes.push(variants[selectedVariant]);
            }
        }

        // Add custom className
        if (className) {
            classes.push(className);
        }

        return cn(...classes);
    };
}

/**
 * Common focus ring styles for interactive elements.
 * Returns a class string for consistent focus styling.
 */
export const focusRing = cn(
    'focus-visible:outline-none',
    'focus-visible:ring-2',
    'focus-visible:ring-ring',
    'focus-visible:ring-offset-2',
    'focus-visible:ring-offset-background'
);

/**
 * Common disabled styles for interactive elements.
 */
export const disabledStyles = cn('disabled:pointer-events-none', 'disabled:opacity-50');

/**
 * Formats a date using Intl.DateTimeFormat.
 * @param date - Date to format
 * @param options - Intl.DateTimeFormatOptions
 * @param locale - Locale string (default: 'en-US')
 */
export function formatDate(
    date: Date | string | number,
    options: Intl.DateTimeFormatOptions = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    },
    locale: string = 'en-US'
): string {
    const d = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
    return new Intl.DateTimeFormat(locale, options).format(d);
}

/**
 * Formats a relative time (e.g., "2 days ago", "in 3 hours").
 * @param date - Date to format relative to now
 * @param locale - Locale string (default: 'en-US')
 */
export function formatRelativeTime(date: Date | string | number, locale: string = 'en-US'): string {
    const d = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date;
    const now = new Date();
    const diffInSeconds = Math.floor((d.getTime() - now.getTime()) / 1000);

    const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });

    const intervals: { unit: Intl.RelativeTimeFormatUnit; seconds: number }[] = [
        { unit: 'year', seconds: 31536000 },
        { unit: 'month', seconds: 2592000 },
        { unit: 'week', seconds: 604800 },
        { unit: 'day', seconds: 86400 },
        { unit: 'hour', seconds: 3600 },
        { unit: 'minute', seconds: 60 },
        { unit: 'second', seconds: 1 },
    ];

    for (const { unit, seconds } of intervals) {
        const interval = Math.floor(Math.abs(diffInSeconds) / seconds);
        if (interval >= 1) {
            return rtf.format(diffInSeconds > 0 ? interval : -interval, unit);
        }
    }

    return rtf.format(0, 'second');
}

/**
 * Generates a random ID for use in components.
 * @param prefix - Optional prefix for the ID
 */
export function generateId(prefix: string = 'id'): string {
    return `${prefix}-${Math.random().toString(36).substring(2, 11)}`;
}

/**
 * Debounces a function call.
 * @param fn - Function to debounce
 * @param delay - Delay in milliseconds
 */
export function debounce<T extends (...args: Parameters<T>) => void>(
    fn: T,
    delay: number
): (...args: Parameters<T>) => void {
    let timeoutId: ReturnType<typeof setTimeout>;
    return (...args: Parameters<T>) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn(...args), delay);
    };
}

/**
 * Throttles a function call.
 * @param fn - Function to throttle
 * @param limit - Minimum time between calls in milliseconds
 */
export function throttle<T extends (...args: Parameters<T>) => void>(
    fn: T,
    limit: number
): (...args: Parameters<T>) => void {
    let inThrottle: boolean;
    return (...args: Parameters<T>) => {
        if (!inThrottle) {
            fn(...args);
            inThrottle = true;
            setTimeout(() => (inThrottle = false), limit);
        }
    };
}
