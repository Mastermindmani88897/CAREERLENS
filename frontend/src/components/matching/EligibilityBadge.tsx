/**
 * Phase 20 EligibilityBadge Component.
 * Displays candidate eligibility status: ELIGIBLE, PARTIAL, or REVIEW_REQUIRED.
 * Provides accessible labels and distinctive visual indicators.
 */

import { AlertOctagon, AlertTriangle, CheckCircle2 } from 'lucide-react'
import type { EligibilityStatus } from '@/types/matching'
import { cn } from '@/lib/utils'

interface EligibilityBadgeProps {
  status: EligibilityStatus
  className?: string
  showDescription?: boolean
}

interface StatusConfig {
  label: string
  ariaLabel: string
  description: string
  badgeClass: string
  icon: typeof CheckCircle2
}

const STATUS_CONFIGS: Record<EligibilityStatus, StatusConfig> = {
  eligible: {
    label: 'ELIGIBLE',
    ariaLabel: 'Eligibility status: Eligible. Meets core qualifications.',
    description: 'Candidate profile aligns well with required skills and criteria.',
    badgeClass:
      'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20',
    icon: CheckCircle2,
  },
  partial: {
    label: 'PARTIAL',
    ariaLabel: 'Eligibility status: Partial. Meets some criteria but has gaps.',
    description: 'Meets several criteria but has noticeable skill or qualification gaps.',
    badgeClass:
      'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30 hover:bg-amber-500/20',
    icon: AlertTriangle,
  },
  review_required: {
    label: 'REVIEW REQUIRED',
    ariaLabel: 'Eligibility status: Review Required. Contains significant gaps or conflicts.',
    description: 'Requires closer manual review due to significant shortfall or conflict.',
    badgeClass:
      'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30 hover:bg-rose-500/20',
    icon: AlertOctagon,
  },
}

export function EligibilityBadge({
  status,
  className,
  showDescription = false,
}: EligibilityBadgeProps) {
  const config = STATUS_CONFIGS[status] || STATUS_CONFIGS.partial
  const Icon = config.icon

  return (
    <div className={cn('inline-flex flex-col gap-0.5', className)}>
      <span
        role="status"
        aria-label={config.ariaLabel}
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border transition-colors',
          config.badgeClass
        )}
      >
        <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>{config.label}</span>
      </span>
      {showDescription && (
        <span className="text-[11px] text-muted-foreground mt-0.5 max-w-xs">
          {config.description}
        </span>
      )}
    </div>
  )
}
