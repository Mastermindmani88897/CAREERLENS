/**
 * Phase 20 MatchWarningsList Component.
 * Displays structured eligibility warnings and review triggers returned by the backend.
 */

import { AlertTriangle, AlertCircle } from 'lucide-react'

interface MatchWarningsListProps {
  warnings: string[] | null | undefined
  className?: string
}

export function MatchWarningsList({ warnings, className = '' }: MatchWarningsListProps) {
  if (!warnings || warnings.length === 0) {
    return null
  }

  return (
    <div
      role="alert"
      className={`rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 space-y-2.5 ${className}`}
    >
      <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-semibold text-xs sm:text-sm">
        <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
        <span>Eligibility Warnings & Gaps ({warnings.length})</span>
      </div>

      <p className="text-xs text-amber-700/90 dark:text-amber-300/80 leading-relaxed">
        The backend engine detected key criteria that may require manual review or profile updates before applying:
      </p>

      <ul className="space-y-1.5 pl-2 list-none text-xs text-amber-900 dark:text-amber-200">
        {warnings.map((warning, idx) => (
          <li key={`warning-${idx}`} className="flex items-start gap-2">
            <AlertCircle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" aria-hidden="true" />
            <span className="leading-snug">{warning}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
