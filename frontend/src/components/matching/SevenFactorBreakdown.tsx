/**
 * Phase 20 SevenFactorBreakdown Component.
 * Visualizes the approved seven-factor scoring breakdown:
 * 1. Semantic Similarity (35%)
 * 2. Skill Overlap (25%)
 * 3. Experience (15%)
 * 4. Education (10%)
 * 5. Location (5%)
 * 6. Work Mode (5%)
 * 7. Employment Type (5%)
 */

import {
  BookOpen,
  Briefcase,
  CheckCircle2,
  Clock,
  Compass,
  FileCheck2,
  Globe,
  Sparkles,
  XCircle,
} from 'lucide-react'
import type { ScoreBreakdown } from '@/types/matching'

interface SevenFactorBreakdownProps {
  breakdown: ScoreBreakdown
  className?: string
}

interface FactorItem {
  id: string
  title: string
  weight: number
  score: number
  icon: typeof Sparkles
  detail: string
  subtext?: string
  isMet?: boolean
}

export function SevenFactorBreakdown({ breakdown, className = '' }: SevenFactorBreakdownProps) {
  const {
    weights,
    skill_overlap,
    experience,
    education,
    location,
    work_mode,
    location_work_mode,
    employment_type,
    semantic_similarity_normalized,
    semantic_similarity_raw,
  } = breakdown

  // Normalize location & work mode fallback if individual breakdowns are null
  const locScore = location ? location.score : location_work_mode.score
  const locDetail = location
    ? `${location.candidate_location || 'Profile not set'} vs ${location.opportunity_location || 'Any'}${
        location.open_to_relocation ? ' (Open to relocation)' : ''
      }`
    : `Work mode: ${location_work_mode.opportunity_work_mode}`

  const wmScore = work_mode ? work_mode.score : location_work_mode.score
  const wmDetail = work_mode
    ? `Preferred: ${work_mode.candidate_preferred_work_mode} | Role: ${work_mode.opportunity_work_mode}`
    : `Role: ${location_work_mode.opportunity_work_mode}`

  const factors: FactorItem[] = [
    {
      id: 'semantic',
      title: 'Semantic Similarity',
      weight: weights.semantic_similarity,
      score: semantic_similarity_normalized,
      icon: Sparkles,
      detail: `Raw cosine: ${semantic_similarity_raw >= 0 ? '+' : ''}${semantic_similarity_raw.toFixed(
        2
      )} (vector alignment)`,
      subtext: 'Matches resume text and narrative with job description keywords',
    },
    {
      id: 'skills',
      title: 'Required & Preferred Skills',
      weight: weights.skill_overlap,
      score: skill_overlap.score,
      icon: FileCheck2,
      detail: `${skill_overlap.matched_required.length}/${skill_overlap.required_count} required, ${skill_overlap.matched_preferred.length}/${skill_overlap.preferred_count} preferred`,
      subtext: 'Calculated from deterministic keyword extraction and skill mappings',
    },
    {
      id: 'experience',
      title: 'Experience Duration',
      weight: weights.experience,
      score: experience.score,
      icon: Clock,
      detail: `${experience.candidate_total_years.toFixed(1)} yrs candidate vs ${
        experience.required_min_years !== null ? `${experience.required_min_years} yrs min` : 'No minimum'
      }${experience.is_overqualified ? ' (Overqualified flag)' : ''}`,
      subtext: 'Considers merged overlapping roles and soft penalties',
    },
    {
      id: 'education',
      title: 'Education Attainment',
      weight: weights.education,
      score: education.score,
      icon: BookOpen,
      detail: `Candidate: ${education.candidate_highest_level} vs Required: ${education.required_level}`,
      isMet: education.meets_requirement,
      subtext: education.missing_evidence
        ? 'Missing education evidence in profile'
        : education.meets_requirement
        ? 'Meets or exceeds required level'
        : 'Below stated education requirement',
    },
    {
      id: 'location',
      title: 'Geographic Location',
      weight: weights.location || 0.05,
      score: locScore,
      icon: Globe,
      detail: locDetail,
      subtext: 'Matches candidate location, willingness to relocate, or remote eligibility',
    },
    {
      id: 'work_mode',
      title: 'Work Mode Alignment',
      weight: weights.work_mode || 0.05,
      score: wmScore,
      icon: Compass,
      detail: wmDetail,
      subtext: work_mode?.has_conflict ? 'Work mode conflict detected' : 'Compatible work arrangement',
    },
    {
      id: 'employment_type',
      title: 'Employment Type',
      weight: weights.employment_type,
      score: employment_type.score,
      icon: Briefcase,
      detail: `Preferred: ${employment_type.candidate_preferred_employment_type} | Role: ${employment_type.opportunity_employment_type}`,
      isMet: employment_type.is_match,
      subtext: employment_type.is_missing
        ? 'No candidate preference specified'
        : employment_type.is_match
        ? 'Matches candidate employment type'
        : 'Employment type mismatch',
    },
  ]

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'bg-emerald-500'
    if (score >= 0.5) return 'bg-amber-500'
    return 'bg-rose-500'
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between border-b border-border/60 pb-3">
        <div>
          <h3 className="text-base font-bold text-foreground">Seven-Factor Score Breakdown</h3>
          <p className="text-xs text-muted-foreground">
            Backend-calculated multi-factor scoring matching approved weights.
          </p>
        </div>
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-muted text-muted-foreground">
          Total: 100%
        </span>
      </div>

      <div className="space-y-3.5" role="region" aria-label="Seven factor scoring breakdown details">
        {factors.map((factor) => {
          const FactorIcon = factor.icon
          const factorPercentage = Math.round(factor.score * 100)
          const weightPercentage = Math.round(factor.weight * 100)

          return (
            <div
              key={factor.id}
              className="p-3.5 rounded-lg border border-border/70 bg-card hover:border-border transition-colors space-y-2"
            >
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 text-primary">
                    <FactorIcon className="h-3.5 w-3.5" aria-hidden="true" />
                  </div>
                  <div>
                    <span className="font-semibold text-foreground mr-2">{factor.title}</span>
                    <span className="text-[11px] font-medium text-muted-foreground">
                      ({weightPercentage}% weight)
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {factor.isMet !== undefined && (
                    factor.isMet ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" aria-label="Requirement met" />
                    ) : (
                      <XCircle className="h-3.5 w-3.5 text-rose-500" aria-label="Requirement not met" />
                    )
                  )}
                  <span className="font-bold text-foreground" aria-label={`${factor.title} score: ${factorPercentage}%`}>
                    {factorPercentage}%
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${getScoreColor(factor.score)}`}
                  style={{ width: `${Math.min(100, Math.max(0, factorPercentage))}%` }}
                />
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between text-[11px] text-muted-foreground gap-1 pt-0.5">
                <span className="font-medium text-foreground/80">{factor.detail}</span>
                {factor.subtext && <span className="text-muted-foreground/90">{factor.subtext}</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
