'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

type AvatarStatus = 'idle' | 'loading' | 'loaded' | 'error';

interface AvatarContextValue {
  status: AvatarStatus;
  setStatus: (status: AvatarStatus) => void;
}

const AvatarContext = React.createContext<AvatarContextValue | null>(null);

const Avatar = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    const [status, setStatus] = React.useState<AvatarStatus>('idle');

    return (
      <AvatarContext.Provider value={{ status, setStatus }}>
        <div
          ref={ref}
          className={cn('relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full', className)}
          {...props}
        >
          {children}
        </div>
      </AvatarContext.Provider>
    );
  }
);
Avatar.displayName = 'Avatar';

const AvatarImage = React.forwardRef<HTMLImageElement, React.ImgHTMLAttributes<HTMLImageElement>>(
  ({ className, src, ...props }, ref) => {
    const context = React.useContext(AvatarContext);

    React.useEffect(() => {
      if (!src) {
        context?.setStatus('error');
      } else {
        context?.setStatus('loading');
      }
    }, [src, context]);

    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        ref={ref}
        src={src}
        alt=""
        className={cn(
          'aspect-square h-full w-full object-cover',
          className,
          context?.status !== 'loaded' && 'hidden'
        )}
        onLoad={() => context?.setStatus('loaded')}
        onError={() => context?.setStatus('error')}
        {...props}
      />
    );
  }
);
AvatarImage.displayName = 'AvatarImage';

const AvatarFallback = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    const context = React.useContext(AvatarContext);

    // Show fallback if loading or error
    if (context?.status === 'loaded') return null;

    return (
      <div
        ref={ref}
        className={cn(
          'flex h-full w-full items-center justify-center rounded-full bg-muted',
          className
        )}
        {...props}
      />
    );
  }
);
AvatarFallback.displayName = 'AvatarFallback';

export { Avatar, AvatarImage, AvatarFallback };
