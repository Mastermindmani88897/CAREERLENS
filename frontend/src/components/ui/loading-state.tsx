import * as React from 'react'
import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'

interface LoadingStateProps extends React.HTMLAttributes<HTMLDivElement> {
  message?: string
  size?: 'sm' | 'md' | 'lg'
}

export function LoadingState({
  message = 'Loading CareerLens content...',
  size = 'md',
  className,
  ...props
}: LoadingStateProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'flex flex-col items-center justify-center space-y-3 py-12 text-center text-muted-foreground',
        className
      )}
      {...props}
    >
      <Loader2
        className={cn('animate-spin text-primary', sizeClasses[size])}
        aria-hidden="true"
      />
      <span className="text-sm font-medium">{message}</span>
      <span className="sr-only">Loading</span>
    </div>
  )
}
