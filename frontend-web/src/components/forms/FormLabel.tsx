'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface FormLabelProps {
  htmlFor: string;
  children: React.ReactNode;
  required?: boolean;
  className?: string;
}

export function FormLabel({ htmlFor, children, required = false, className = '' }: FormLabelProps) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn(
        'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
        className
      )}
    >
      {children}
      {required && (
        <span className="text-destructive ml-1" aria-label="required">
          *
        </span>
      )}
    </label>
  );
}
