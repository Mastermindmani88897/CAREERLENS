import React from 'react'
import {
  Bookmark,
  Send,
  FileCode,
  CalendarCheck,
  Award,
  XCircle,
  Archive,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  APPLICATION_STATUS_LABELS,
  type ApplicationStatus,
} from '@/types/application'

interface ApplicationStatusBadgeProps {
  status: ApplicationStatus
  className?: string
  showIcon?: boolean
}

export function ApplicationStatusBadge({
  status,
  className,
  showIcon = true,
}: ApplicationStatusBadgeProps) {
  const label = APPLICATION_STATUS_LABELS[status] || status

  let styleClasses = ''
  let icon: React.ReactNode = null

  switch (status) {
    case 'saved':
      styleClasses =
        'bg-slate-100 text-slate-700 dark:bg-slate-800/60 dark:text-slate-300 border-slate-200 dark:border-slate-700'
      icon = <Bookmark className="h-3 w-3 mr-1 text-slate-500" aria-hidden="true" />
      break
    case 'applied':
      styleClasses =
        'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border-blue-200 dark:border-blue-800'
      icon = <Send className="h-3 w-3 mr-1 text-blue-600 dark:text-blue-400" aria-hidden="true" />
      break
    case 'oa':
      styleClasses =
        'bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300 border-purple-200 dark:border-purple-800'
      icon = <FileCode className="h-3 w-3 mr-1 text-purple-600 dark:text-purple-400" aria-hidden="true" />
      break
    case 'interview':
      styleClasses =
        'bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300 border-amber-200 dark:border-amber-800'
      icon = <CalendarCheck className="h-3 w-3 mr-1 text-amber-600 dark:text-amber-400" aria-hidden="true" />
      break
    case 'offer':
      styleClasses =
        'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800'
      icon = <Award className="h-3 w-3 mr-1 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
      break
    case 'rejected':
      styleClasses =
        'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 border-rose-200 dark:border-rose-800'
      icon = <XCircle className="h-3 w-3 mr-1 text-rose-600 dark:text-rose-400" aria-hidden="true" />
      break
    case 'withdrawn':
      styleClasses =
        'bg-zinc-100 text-zinc-600 dark:bg-zinc-800/50 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700'
      icon = <Archive className="h-3 w-3 mr-1 text-zinc-500" aria-hidden="true" />
      break
  }

  return (
    <Badge
      variant="outline"
      role="status"
      aria-label={`Status: ${label}`}
      className={cn('inline-flex items-center text-xs font-medium px-2.5 py-0.5 border', styleClasses, className)}
    >
      {showIcon && icon}
      <span>{label}</span>
    </Badge>
  )
}
