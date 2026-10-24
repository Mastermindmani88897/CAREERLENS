/**
 * Phase 20 MatchScoreCard Component.
 * Displays final hybrid match score, semantic vs deterministic subscores,
 * eligibility badge, and explicit ranking-aid disclaimer.
 */

import { Info, Sparkles, Target } from 'lucide-react'
import { EligibilityBadge } from '@/components/matching/EligibilityBadge'
import type { EligibilityStatus } from '@/types/matching'

interface MatchScoreCardProps {
  finalScore: number
  semanticScore: number
  deterministicScore: number
  eligibilityStatus: EligibilityStatus
  computedAt?: string
  className?: string
}

export function MatchScoreCard({
  finalScore,
  semanticScore,
  deterministicScore,
  eligibilityStatus,
  computedAt,
  className = '',
}: MatchScoreCardProps) {
  const percentage = Math.round(finalScore * 100)
  const semPercentage = Math.round(semanticScore * 100)
  const detPercentage = Math.round(deterministicScore * 100)

  // Determine score color accent
  const getScoreColor = () => {
    if (finalScore >= 0.7) return 'text-emerald-600 dark:text-emerald-400'
    if (finalScore >= 0.45) return 'text-amber-600 dark:text-amber-400'
    return 'text-rose-600 dark:text-rose-400'
  }

  const getProgressBg = () => {
    if (finalScore >= 0.7) return 'bg-emerald-500'
    if (finalScore >= 0.45) return 'bg-amber-500'
    return 'bg-rose-500'
  }

  return (
    <div
      className={`rounded-xl border border-border bg-card p-6 shadow-sm space-y-5 ${className}`}
      aria-label="Match score evaluation results"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block mb-1">
            Hybrid Match Evaluation
          </span>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-4xl sm:text-5xl font-extrabold tracking-tight ${getScoreColor()}`}
              aria-label={`Overall hybrid match score: ${percentage} percent`}
            >
              {percentage}%
            </span>
            <span className="text-sm font-medium text-muted-foreground">Match Score</span>
          </div>
        </div>

        <div className="flex flex-col sm:items-end gap-1.5">
          <EligibilityBadge status={eligibilityStatus} showDescription />
          {computedAt && (
            <span className="text-[11px] text-muted-foreground">
              Evaluated {new Date(computedAt).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>

      {/* Visual score bar */}
      <div className="space-y-1.5">
        <div className="h-2.5 w-full rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${getProgressBg()}`}
            style={{ width: `${Math.min(100, Math.max(0, percentage))}%` }}
          />
        </div>
        <div className="flex justify-between text-[11px] text-muted-foreground">
          <span>0%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
      </div>

      {/* Subscores: Semantic Alignment & Deterministic Alignment */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-border/60">
        <div className="flex items-center justify-between p-2.5 rounded-lg bg-muted/40 border border-border/40">
          <div className="flex items-center gap-2 text-xs">
            <Sparkles className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
            <span className="text-muted-foreground">Semantic Alignment</span>
          </div>
          <span className="text-xs font-bold text-foreground">{semPercentage}%</span>
        </div>

        <div className="flex items-center justify-between p-2.5 rounded-lg bg-muted/40 border border-border/40">
          <div className="flex items-center gap-2 text-xs">
            <Target className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
            <span className="text-muted-foreground">Deterministic Criteria</span>
          </div>
          <span className="text-xs font-bold text-foreground">{detPercentage}%</span>
        </div>
      </div>

      {/* Mandatory Disclaimer */}
      <div
        className="flex items-start gap-2 p-3 rounded-lg bg-muted/50 border border-border/60 text-xs text-muted-foreground leading-relaxed"
        role="note"
      >
        <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" aria-hidden="true" />
        <p>
          <strong className="text-foreground font-semibold">Ranking Aid Disclaimer:</strong> A
          match score is a ranking aid to help prioritize opportunities based on profile
          data and job descriptions. It does not guarantee job suitability, interview selection,
          or hiring outcomes.
        </p>
      </div>
    </div>
  )
}
