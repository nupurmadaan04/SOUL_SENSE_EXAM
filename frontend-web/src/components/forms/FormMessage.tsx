'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface FormMessageProps {
  name: string;
  message?: string;
  className?: string;
}

export function FormMessage({ name, message, className = '' }: FormMessageProps) {
  if (!message) return null;

  return (
    <div className={cn('text-sm text-muted-foreground', className)} id={`${name}-message`}>
      {message}
    </div>
  );
}
