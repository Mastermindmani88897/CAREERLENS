/**
 * RecommendationCard component for Phase 18 Recommendations.
 * Renders an opportunity overview card with structured metadata, badges, plain-text snippets,
 * and a neutral semantic similarity indicator (raw vector cosine alignment in [-1.0, 1.0]).
 * Never uses dangerouslySetInnerHTML, hiring probabilities, or artificial fit percentages.
 */

import { Link } from 'react-router-dom'
import {
  Briefcase,
  Building2,
  Calendar,
  DollarSign,
  HelpCircle,
  MapPin,
  Sparkles,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import type { SemanticOpportunityItem } from '@/types/recommendation'

interface RecommendationCardProps {
  item: SemanticOpportunityItem
}

/**
 * Format raw cosine similarity into a neutral display score.
 * Explains vector text similarity without presenting hiring probabilities.
 */
function formatSemanticScore(similarity: number | null | undefined): {
  label: string
  text: string
  ariaLabel: string
} {
  if (similarity === null || similarity === undefined || Number.isNaN(similarity)) {
    return {
      label: 'Alignment: N/A',
      text: 'Semantic alignment score is unavailable for this listing.',
      ariaLabel: 'Semantic alignment not available',
    }
  }

  const rounded = similarity.toFixed(2)

  if (similarity <= 0) {
    return {
      label: `Cosine: ${rounded} (Low)`,
      text: `Raw cosine similarity: ${rounded}. Indicates low or orthogonal semantic alignment between candidate profile and opportunity text.`,
      ariaLabel: `Low semantic alignment with cosine score of ${rounded}`,
    }
  }

  return {
    label: `Cosine: +${rounded}`,
    text: `Raw cosine similarity: +${rounded}. Reflects semantic vector alignment between your profile and this listing. Does not evaluate hiring eligibility or qualifications.`,
    ariaLabel: `Semantic alignment cosine score of plus ${rounded}`,
  }
}

export function RecommendationCard({ item }: RecommendationCardProps) {
  // Format opportunity type badges
  const typeBadgeVariant =
    item.opportunity_type === 'hackathon'
      ? 'secondary'
      : item.opportunity_type === 'internship'
      ? 'outline'
      : 'default'

  // Format compensation
  const formatSalary = () => {
    if (!item.salary_min && !item.salary_max) return null
    const curr = item.salary_currency || 'USD'
    if (item.salary_min && item.salary_max) {
      return `${curr} ${item.salary_min.toLocaleString('en-US')} - ${item.salary_max.toLocaleString('en-US')}`
    }
    if (item.salary_min) {
      return `${curr} ${item.salary_min.toLocaleString('en-US')}+`
    }
    return `Up to ${curr} ${item.salary_max?.toLocaleString('en-US')}`
  }

  // Format location
  const locationText = [
    item.location_city,
    item.location_state,
    item.location_country,
  ]
    .filter(Boolean)
    .join(', ')

  // Format experience requirement
  const formatExperience = () => {
    if (
      item.min_experience_years === null &&
      item.max_experience_years === null
    ) {
      return null
    }
    if (
      item.min_experience_years !== null &&
      item.max_experience_years !== null
    ) {
      return `${item.min_experience_years}–${item.max_experience_years} yrs exp`
    }
    if (item.min_experience_years !== null) {
      return `${item.min_experience_years}+ yrs exp`
    }
    return `Up to ${item.max_experience_years} yrs exp`
  }

  const salaryDisplay = formatSalary()
  const expDisplay = formatExperience()
  const scoreInfo = formatSemanticScore(item.semantic_similarity)

  // Skills chips preview (up to 4)
  const skillsList = item.required_skills || []
  const previewSkills = skillsList.slice(0, 4)
  const remainingSkillsCount = skillsList.length - previewSkills.length

  return (
    <Card className="flex flex-col h-full hover:border-primary/50 transition-colors duration-200">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <Badge variant={typeBadgeVariant} className="capitalize">
                {item.opportunity_type}
              </Badge>
              <Badge variant="outline" className="capitalize">
                {item.work_mode}
              </Badge>
              {item.employment_type && (
                <Badge variant="secondary" className="capitalize text-xs">
                  {item.employment_type}
                </Badge>
              )}

              {/* Semantic Similarity Neutral Badge */}
              <div
                className="inline-flex items-center gap-1 rounded-md bg-secondary/80 px-2 py-0.5 text-xs font-medium text-secondary-foreground"
                title={scoreInfo.text}
                aria-label={scoreInfo.ariaLabel}
              >
                <Sparkles className="h-3 w-3 text-primary shrink-0" aria-hidden="true" />
                <span>{scoreInfo.label}</span>
                <span className="sr-only">({scoreInfo.text})</span>
                <HelpCircle className="h-3 w-3 text-muted-foreground/70 shrink-0" aria-hidden="true" />
              </div>
            </div>

            <CardTitle className="text-lg font-bold line-clamp-1">
              <Link
                to={`/opportunities/${item.id}`}
                className="hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
              >
                {item.title}
              </Link>
            </CardTitle>

            <div className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground mt-1">
              <Building2 className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="line-clamp-1">{item.company}</span>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 pb-4 space-y-3">
        {/* Meta badges / rows */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-muted-foreground">
          {locationText && (
            <div className="flex items-center gap-1.5 line-clamp-1">
              <MapPin className="h-3.5 w-3.5 shrink-0 text-primary/70" aria-hidden="true" />
              <span>{locationText}</span>
            </div>
          )}

          {salaryDisplay && (
            <div className="flex items-center gap-1.5 line-clamp-1 font-medium text-foreground">
              <DollarSign className="h-3.5 w-3.5 shrink-0 text-emerald-500" aria-hidden="true" />
              <span>{salaryDisplay}</span>
            </div>
          )}

          {expDisplay && (
            <div className="flex items-center gap-1.5 line-clamp-1">
              <Briefcase className="h-3.5 w-3.5 shrink-0 text-primary/70" aria-hidden="true" />
              <span>{expDisplay}</span>
            </div>
          )}

          {item.application_deadline && (
            <div className="flex items-center gap-1.5 line-clamp-1">
              <Calendar className="h-3.5 w-3.5 shrink-0 text-amber-500" aria-hidden="true" />
              <span>Deadline: {item.application_deadline}</span>
            </div>
          )}
        </div>

        {/* Text snippet - Plain text, no HTML */}
        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
          {item.description}
        </p>

        {/* Required skills preview */}
        {previewSkills.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {previewSkills.map((skill, idx) => (
              <span
                key={`${skill}-${idx}`}
                className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
              >
                {skill}
              </span>
            ))}
            {remainingSkillsCount > 0 && (
              <span className="inline-flex items-center rounded-md bg-muted/60 px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground">
                +{remainingSkillsCount} more
              </span>
            )}
          </div>
        )}
      </CardContent>

      <CardFooter className="pt-2 border-t border-border/60 flex items-center justify-between text-xs text-muted-foreground">
        <span>
          Posted{' '}
          {item.posted_date ||
            new Date(item.created_at).toLocaleDateString()}
        </span>
        <Link
          to={`/opportunities/${item.id}`}
          className="font-medium text-primary hover:underline"
        >
          View Details &rarr;
        </Link>
      </CardFooter>
    </Card>
  )
}
