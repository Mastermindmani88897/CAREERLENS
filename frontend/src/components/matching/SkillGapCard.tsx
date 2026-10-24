/**
 * Phase 20 SkillGapCard Component.
 * Visualizes matched vs missing required skills, and matched vs missing preferred skills.
 */

import { Check, CheckCircle2, FileQuestion, X, XCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { SkillGap } from '@/types/matching'

interface SkillGapCardProps {
  skillGap: SkillGap
  className?: string
}

export function SkillGapCard({ skillGap, className = '' }: SkillGapCardProps) {
  const {
    matched_required_skills = [],
    missing_required_skills = [],
    matched_preferred_skills = [],
    missing_preferred_skills = [],
  } = skillGap

  const hasAnySkills =
    matched_required_skills.length > 0 ||
    missing_required_skills.length > 0 ||
    matched_preferred_skills.length > 0 ||
    missing_preferred_skills.length > 0

  return (
    <div className={`space-y-4 rounded-xl border border-border bg-card p-5 ${className}`}>
      <div className="flex items-center justify-between border-b border-border/60 pb-3">
        <div>
          <h3 className="text-base font-bold text-foreground">Skill Gap Analysis</h3>
          <p className="text-xs text-muted-foreground">
            Comparison of your verified skills against opportunity requirements.
          </p>
        </div>
      </div>

      {!hasAnySkills ? (
        <div className="flex items-center gap-2 py-4 text-xs text-muted-foreground">
          <FileQuestion className="h-4 w-4" />
          <span>No specific skill requirements specified for this role.</span>
        </div>
      ) : (
        <div className="space-y-4 text-xs">
          {/* Matched Required Skills */}
          <div>
            <div className="flex items-center gap-1.5 font-semibold text-emerald-700 dark:text-emerald-400 mb-2">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              <span>Matched Required Skills ({matched_required_skills.length})</span>
            </div>
            {matched_required_skills.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {matched_required_skills.map((skill) => (
                  <Badge
                    key={`matched-req-${skill}`}
                    variant="outline"
                    className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 flex items-center gap-1"
                  >
                    <Check className="h-3 w-3" />
                    <span>{skill}</span>
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic pl-5">
                None matched yet. Consider updating your profile skills.
              </p>
            )}
          </div>

          {/* Missing Required Skills */}
          <div>
            <div className="flex items-center gap-1.5 font-semibold text-rose-700 dark:text-rose-400 mb-2">
              <XCircle className="h-4 w-4" aria-hidden="true" />
              <span>Missing Required Skills ({missing_required_skills.length})</span>
            </div>
            {missing_required_skills.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {missing_required_skills.map((skill) => (
                  <Badge
                    key={`missing-req-${skill}`}
                    variant="outline"
                    className="bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/30 flex items-center gap-1"
                  >
                    <X className="h-3 w-3" />
                    <span>{skill}</span>
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium pl-5">
                Great job! You have all required skills for this opportunity.
              </p>
            )}
          </div>

          {/* Preferred Skills (if any) */}
          {(matched_preferred_skills.length > 0 || missing_preferred_skills.length > 0) && (
            <div className="pt-3 border-t border-border/50 space-y-3">
              {matched_preferred_skills.length > 0 && (
                <div>
                  <span className="text-muted-foreground font-medium block mb-1.5">
                    Matched Preferred Skills ({matched_preferred_skills.length})
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {matched_preferred_skills.map((skill) => (
                      <Badge key={`matched-pref-${skill}`} variant="secondary" className="text-[11px]">
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {missing_preferred_skills.length > 0 && (
                <div>
                  <span className="text-muted-foreground font-medium block mb-1.5">
                    Missing Preferred Skills ({missing_preferred_skills.length})
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {missing_preferred_skills.map((skill) => (
                      <Badge
                        key={`missing-pref-${skill}`}
                        variant="outline"
                        className="text-[11px] text-muted-foreground border-border/60"
                      >
                        {skill}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
