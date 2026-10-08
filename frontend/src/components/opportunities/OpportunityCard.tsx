/**
 * OpportunityCard component for Phase 15 Discovery.
 * Renders an opportunity overview card with structured metadata, badges, and plain-text snippets.
 * Never uses dangerouslySetInnerHTML or AI match percentages.
 */

import { Link } from 'react-router-dom'
import {
  Briefcase,
  Building2,
  Calendar,
  DollarSign,
  MapPin,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import type { Opportunity } from '@/types/opportunity'

interface OpportunityCardProps {
  opportunity: Opportunity
}

export function OpportunityCard({ opportunity }: OpportunityCardProps) {
  // Format opportunity type badges
  const typeBadgeVariant =
    opportunity.opportunity_type === 'hackathon'
      ? 'secondary'
      : opportunity.opportunity_type === 'internship'
      ? 'outline'
      : 'default'

  // Format compensation
  const formatSalary = () => {
    if (!opportunity.salary_min && !opportunity.salary_max) return null
    const curr = opportunity.salary_currency || 'USD'
    if (opportunity.salary_min && opportunity.salary_max) {
      return `${curr} ${opportunity.salary_min.toLocaleString('en-US')} - ${opportunity.salary_max.toLocaleString('en-US')}`
    }
    if (opportunity.salary_min) {
      return `${curr} ${opportunity.salary_min.toLocaleString('en-US')}+`
    }
    return `Up to ${curr} ${opportunity.salary_max?.toLocaleString('en-US')}`
  }

  // Format location
  const locationText = [
    opportunity.location_city,
    opportunity.location_state,
    opportunity.location_country,
  ]
    .filter(Boolean)
    .join(', ')

  // Format experience requirement
  const formatExperience = () => {
    if (
      opportunity.min_experience_years === null &&
      opportunity.max_experience_years === null
    ) {
      return null
    }
    if (
      opportunity.min_experience_years !== null &&
      opportunity.max_experience_years !== null
    ) {
      return `${opportunity.min_experience_years}–${opportunity.max_experience_years} yrs exp`
    }
    if (opportunity.min_experience_years !== null) {
      return `${opportunity.min_experience_years}+ yrs exp`
    }
    return `Up to ${opportunity.max_experience_years} yrs exp`
  }

  const salaryDisplay = formatSalary()
  const expDisplay = formatExperience()

  // Skills chips preview (up to 4)
  const skillsList = opportunity.required_skills || []
  const previewSkills = skillsList.slice(0, 4)
  const remainingSkillsCount = skillsList.length - previewSkills.length

  return (
    <Card className="flex flex-col h-full hover:border-primary/50 transition-colors duration-200">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <Badge variant={typeBadgeVariant} className="capitalize">
                {opportunity.opportunity_type}
              </Badge>
              <Badge variant="outline" className="capitalize">
                {opportunity.work_mode}
              </Badge>
              {opportunity.employment_type && (
                <Badge variant="secondary" className="capitalize text-xs">
                  {opportunity.employment_type}
                </Badge>
              )}
            </div>
            <CardTitle className="text-lg font-bold line-clamp-1">
              <Link
                to={`/opportunities/${opportunity.id}`}
                className="hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
              >
                {opportunity.title}
              </Link>
            </CardTitle>
            <div className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground mt-1">
              <Building2 className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="line-clamp-1">{opportunity.company}</span>
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

          {opportunity.application_deadline && (
            <div className="flex items-center gap-1.5 line-clamp-1">
              <Calendar className="h-3.5 w-3.5 shrink-0 text-amber-500" aria-hidden="true" />
              <span>Deadline: {opportunity.application_deadline}</span>
            </div>
          )}
        </div>

        {/* Text snippet - Plain text, no HTML */}
        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
          {opportunity.description}
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
          {opportunity.posted_date ||
            new Date(opportunity.created_at).toLocaleDateString()}
        </span>
        <Link
          to={`/opportunities/${opportunity.id}`}
          className="font-medium text-primary hover:underline"
        >
          View Details &rarr;
        </Link>
      </CardFooter>
    </Card>
  )
}
