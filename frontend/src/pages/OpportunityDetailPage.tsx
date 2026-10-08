/**
 * OpportunityDetailPage for Phase 15.
 * Complete opportunity detail view with structured metadata, required/preferred skills breakdown,
 * and safe external application links.
 * Content is rendered strictly as plain text (no dangerouslySetInnerHTML, no AI match scores).
 */

import * as React from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Briefcase,
  Building2,
  Calendar,
  CheckCircle2,
  DollarSign,
  ExternalLink,
  GraduationCap,
  MapPin,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ErrorState } from '@/components/ui/error-state'
import { LoadingState } from '@/components/ui/loading-state'
import { getOpportunityById } from '@/services/opportunityService'
import type { OpportunityDetail } from '@/types/opportunity'

export function OpportunityDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [opportunity, setOpportunity] = React.useState<OpportunityDetail | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  const fetchDetail = React.useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const data = await getOpportunityById(id)
      setOpportunity(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load opportunity details.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [id])

  React.useEffect(() => {
    fetchDetail()
  }, [fetchDetail])

  if (loading) {
    return (
      <div className="py-20">
        <LoadingState message="Loading opportunity details..." />
      </div>
    )
  }

  if (error || !opportunity) {
    return (
      <div className="py-12 space-y-4">
        <Link to="/opportunities">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Opportunities
          </Button>
        </Link>
        <ErrorState
          title="Opportunity Not Found"
          description={error || 'The requested opportunity could not be found or has been removed.'}
          onRetry={fetchDetail}
        />
      </div>
    )
  }

  // Safe external URL verification
  const isSafeExternalUrl = (url: string | null): boolean => {
    if (!url) return false
    const trimmed = url.trim().toLowerCase()
    return trimmed.startsWith('http://') || trimmed.startsWith('https://')
  }

  // Format compensation
  const formatSalary = () => {
    if (!opportunity.salary_min && !opportunity.salary_max) return 'Not disclosed'
    const curr = opportunity.salary_currency || 'USD'
    if (opportunity.salary_min && opportunity.salary_max) {
      return `${curr} ${opportunity.salary_min.toLocaleString('en-US')} - ${opportunity.salary_max.toLocaleString('en-US')}`
    }
    if (opportunity.salary_min) {
      return `${curr} ${opportunity.salary_min.toLocaleString('en-US')}+`
    }
    return `Up to ${curr} ${opportunity.salary_max?.toLocaleString('en-US')}`
  }

  // Location string
  const locationText = [
    opportunity.location_city,
    opportunity.location_state,
    opportunity.location_country,
  ]
    .filter(Boolean)
    .join(', ') || 'Not specified'

  // Experience requirement
  const formatExperience = () => {
    if (
      opportunity.min_experience_years === null &&
      opportunity.max_experience_years === null
    ) {
      return 'Not specified'
    }
    if (
      opportunity.min_experience_years !== null &&
      opportunity.max_experience_years !== null
    ) {
      return `${opportunity.min_experience_years} to ${opportunity.max_experience_years} years`
    }
    if (opportunity.min_experience_years !== null) {
      return `${opportunity.min_experience_years}+ years`
    }
    return `Up to ${opportunity.max_experience_years} years`
  }

  // Separate required and preferred relational skills
  const requiredSkills = opportunity.skills.filter((s) => s.is_required)
  const preferredSkills = opportunity.skills.filter((s) => !s.is_required)

  return (
    <div className="space-y-6 pb-16 max-w-5xl mx-auto">
      {/* Back button */}
      <div>
        <Link to="/opportunities">
          <Button variant="ghost" size="sm" className="hover:text-primary">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Opportunities
          </Button>
        </Link>
      </div>

      {/* Main Header Card */}
      <div className="rounded-xl border border-border bg-card p-6 sm:p-8 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="default" className="capitalize text-xs">
                {opportunity.opportunity_type}
              </Badge>
              <Badge variant="outline" className="capitalize text-xs">
                {opportunity.work_mode}
              </Badge>
              {opportunity.employment_type && (
                <Badge variant="secondary" className="capitalize text-xs">
                  {opportunity.employment_type}
                </Badge>
              )}
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
              {opportunity.title}
            </h1>

            <div className="flex items-center gap-2 text-base font-semibold text-muted-foreground">
              <Building2 className="h-5 w-5 text-primary" aria-hidden="true" />
              <span>{opportunity.company}</span>
            </div>
          </div>

          {/* External Apply Button */}
          {opportunity.job_url && isSafeExternalUrl(opportunity.job_url) && (
            <div className="sm:self-center shrink-0">
              <a
                href={opportunity.job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Apply on Official Site
                <ExternalLink className="ml-2 h-4 w-4" aria-hidden="true" />
              </a>
            </div>
          )}
        </div>

        {/* Highlight Metadata Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border/60 text-xs sm:text-sm">
          <div>
            <span className="text-muted-foreground block text-xs mb-0.5">Location</span>
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <MapPin className="h-4 w-4 text-primary shrink-0" />
              <span className="truncate">{locationText}</span>
            </div>
          </div>

          <div>
            <span className="text-muted-foreground block text-xs mb-0.5">Compensation</span>
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <DollarSign className="h-4 w-4 text-emerald-500 shrink-0" />
              <span className="truncate">{formatSalary()}</span>
            </div>
          </div>

          <div>
            <span className="text-muted-foreground block text-xs mb-0.5">Experience</span>
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <Briefcase className="h-4 w-4 text-primary shrink-0" />
              <span className="truncate">{formatExperience()}</span>
            </div>
          </div>

          <div>
            <span className="text-muted-foreground block text-xs mb-0.5">Deadline</span>
            <div className="flex items-center gap-1.5 font-medium text-foreground">
              <Calendar className="h-4 w-4 text-amber-500 shrink-0" />
              <span className="truncate">
                {opportunity.application_deadline || 'Open until filled'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Description and Skills/Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 cols): Full Description */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-bold">About the Opportunity</CardTitle>
            </CardHeader>
            <CardContent>
              {/* Untrusted text safely rendered without dangerouslySetInnerHTML */}
              <div className="text-sm leading-relaxed text-foreground whitespace-pre-line font-sans">
                {opportunity.description}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column (1 col): Structured Skills & Requirements */}
        <div className="space-y-6">
          {/* Relational Skills Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary" />
                Required Skills
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {requiredSkills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {requiredSkills.map((s) => (
                    <Badge key={s.id} variant="default" className="text-xs">
                      {s.skill_name}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">None specified.</p>
              )}

              {preferredSkills.length > 0 && (
                <div className="pt-2 border-t border-border/50">
                  <span className="text-xs font-semibold text-muted-foreground block mb-2">
                    Preferred Skills
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {preferredSkills.map((s) => (
                      <Badge key={s.id} variant="secondary" className="text-xs">
                        {s.skill_name}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Education & Info Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <GraduationCap className="h-4 w-4 text-primary" />
                Eligibility & Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Education Level</span>
                <span className="font-medium capitalize text-foreground">
                  {opportunity.required_education_level}
                </span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-border/40">
                <span className="text-muted-foreground">Source</span>
                <span className="font-medium capitalize text-foreground">
                  {opportunity.source}
                </span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-muted-foreground">Date Listed</span>
                <span className="font-medium text-foreground">
                  {new Date(opportunity.created_at).toLocaleDateString()}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
