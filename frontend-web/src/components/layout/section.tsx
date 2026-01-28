import { cn } from '@/lib/utils';
import React from 'react';

interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode;
  containerClassName?: string;
  isFullWidth?: boolean;
}

export function Section({
  children,
  className,
  containerClassName,
  isFullWidth = false,
  ...props
}: SectionProps) {
  return (
    <section className={cn('py-20 lg:py-32', className)} {...props}>
      <div className={cn(!isFullWidth && 'container mx-auto px-6 lg:px-8', containerClassName)}>
        {children}
      </div>
    </section>
  );
}
