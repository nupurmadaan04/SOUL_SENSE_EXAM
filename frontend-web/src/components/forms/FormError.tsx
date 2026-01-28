'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface FormErrorProps {
  error?: string;
  className?: string;
}

export function FormError({ error, className = '' }: FormErrorProps) {
  if (!error) return null;

  return (
    <div
      className={cn('text-sm font-medium text-destructive', className)}
      role="alert"
      aria-live="polite"
    >
      {error}
    </div>
  );
}
