/**
 * OpportunityDetailPage for Phase 20.
 * Complete opportunity detail view with structured metadata, required/preferred skills,
 * safe external application links, and authenticated hybrid match evaluation integration.
 * Content is rendered strictly as plain text (no dangerouslySetInnerHTML).
 * Match calculations are performed exclusively by the backend matching engine.
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
  LogIn,
  MapPin,
  RefreshCw,
  Sparkles,
  UserPlus,
} from 'lucide-react'

import { EligibilityBadge } from '@/components/matching/EligibilityBadge'
import { MatchExplanationCard } from '@/components/matching/MatchExplanationCard'
import { MatchScoreCard } from '@/components/matching/MatchScoreCard'
import { MatchWarningsList } from '@/components/matching/MatchWarningsList'
import { SevenFactorBreakdown } from '@/components/matching/SevenFactorBreakdown'
import { SkillGapCard } from '@/components/matching/SkillGapCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ErrorState } from '@/components/ui/error-state'
import { LoadingState } from '@/components/ui/loading-state'
import { getMatchByOpportunityId, triggerMatch, MatchingError } from '@/services/matchingService'
import { getOpportunityById } from '@/services/opportunityService'
import type { MatchResponse } from '@/types/matching'
import type { OpportunityDetail } from '@/types/opportunity'

export function OpportunityDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [opportunity, setOpportunity] = React.useState<OpportunityDetail | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  // Matching evaluation state
  const [isAuthenticated, setIsAuthenticated] = React.useState<boolean>(false)
  const [match, setMatch] = React.useState<MatchResponse | null>(null)
  const [matchLoading, setMatchLoading] = React.useState(false)
  const [evaluating, setEvaluating] = React.useState(false)
  const [matchError, setMatchError] = React.useState<string | null>(null)
  const [profileMissing, setProfileMissing] = React.useState(false)

  // Check authentication status on mount
  React.useEffect(() => {
    const token = localStorage.getItem('access_token')
    setIsAuthenticated(Boolean(token))
  }, [])

  // Fetch opportunity detail
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

  // Fetch cached match evaluation (if authenticated, read-only GET lookup)
  const loadExistingMatch = React.useCallback(async () => {
    if (!id) return
    const token = localStorage.getItem('access_token')
    if (!token) return

    setMatchLoading(true)
    setMatchError(null)
    setProfileMissing(false)
    try {
      const existingMatch = await getMatchByOpportunityId(id, token)
      setMatch(existingMatch)
    } catch (err: unknown) {
      if (err instanceof MatchingError && err.status === 404) {
        if (err.message.toLowerCase().includes('candidate profile not found')) {
          setProfileMissing(true)
        }
      } else {
        const msg = err instanceof Error ? err.message : 'Failed to load match record.'
        setMatchError(msg)
      }
    } finally {
      setMatchLoading(false)
    }
  }, [id])

  React.useEffect(() => {
    fetchDetail()
  }, [fetchDetail])

  React.useEffect(() => {
    if (isAuthenticated) {
      loadExistingMatch()
    }
  }, [isAuthenticated, loadExistingMatch])

  // Explicit user-triggered evaluation (avoids expensive calculation on every render)
  const handleEvaluateMatch = async () => {
    if (!id) return
    setEvaluating(true)
    setMatchError(null)
    setProfileMissing(false)
    try {
      const result = await triggerMatch(id)
      setMatch(result)
    } catch (err: unknown) {
      if (err instanceof MatchingError) {
        if (err.status === 404 && err.message.toLowerCase().includes('candidate profile')) {
          setProfileMissing(true)
        } else {
          setMatchError(err.message)
        }
      } else if (err instanceof Error) {
        setMatchError(err.message)
      } else {
        setMatchError('Failed to evaluate match. Please try again.')
      }
    } finally {
      setEvaluating(false)
    }
  }

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
      <div className="rounded-xl border border-border bg-card p-6 sm:p-8 space-y-4 shadow-sm">
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
              {match && (
                <EligibilityBadge status={match.eligibility_status} />
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

      {/* Personalized Match Evaluation Section */}
      <section aria-label="Personalized Match Evaluation" className="space-y-4">
        {!isAuthenticated ? (
          /* Unauthenticated Prompt */
          <div className="rounded-xl border border-dashed border-border bg-muted/30 p-6 text-center space-y-3">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Sparkles className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="space-y-1">
              <h2 className="text-base font-bold text-foreground">Personalized Match & Eligibility Evaluation</h2>
              <p className="text-xs text-muted-foreground max-w-lg mx-auto">
                Sign in to view your multi-factor hybrid match score, seven-factor breakdown, skill gap analysis, and eligibility status for this role.
              </p>
            </div>
            <Link to="/login">
              <Button size="sm" className="mt-2">
                <LogIn className="mr-2 h-4 w-4" />
                Sign In to Evaluate Match
              </Button>
            </Link>
          </div>
        ) : profileMissing ? (
          /* Profile Missing Notice */
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 space-y-3">
            <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-bold text-sm">
              <UserPlus className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              <span>Candidate Profile Required for Match Scoring</span>
            </div>
            <p className="text-xs text-amber-700/90 dark:text-amber-300/80 leading-relaxed">
              We could not find an active candidate profile for your account. Please create or update your profile with your skills, experience, and education to evaluate match alignment.
            </p>
            <Link to="/profile">
              <Button size="sm" variant="default">
                Create Candidate Profile
              </Button>
            </Link>
          </div>
        ) : matchLoading ? (
          /* Loading cached match */
          <div className="p-8 rounded-xl border border-border bg-card">
            <LoadingState message="Checking existing match evaluation..." />
          </div>
        ) : !match ? (
          /* Match not yet evaluated for this opportunity */
          <div className="rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <h2 className="text-base font-bold text-foreground">Evaluate Your Fit for This Role</h2>
              </div>
              <p className="text-xs text-muted-foreground max-w-xl">
                Run the CareerLens hybrid matching engine to evaluate your profile alignment against this opportunity across 7 factors (semantic similarity, skills, experience, education, location, work mode, and employment type).
              </p>
            </div>
            <Button
              onClick={handleEvaluateMatch}
              disabled={evaluating}
              className="shrink-0"
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${evaluating ? 'animate-spin' : ''}`} />
              {evaluating ? 'Evaluating Match...' : 'Evaluate Match'}
            </Button>
          </div>
        ) : (
          /* Evaluated Match Results */
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <h2 className="text-base font-bold text-foreground">Match Evaluation & Eligibility Analysis</h2>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleEvaluateMatch}
                disabled={evaluating}
              >
                <RefreshCw className={`mr-2 h-3.5 w-3.5 ${evaluating ? 'animate-spin' : ''}`} />
                {evaluating ? 'Re-evaluating...' : 'Re-evaluate Match'}
              </Button>
            </div>

            {/* Match Score Card with Disclaimer */}
            <MatchScoreCard
              finalScore={match.final_score}
              semanticScore={match.semantic_score}
              deterministicScore={match.deterministic_score}
              eligibilityStatus={match.eligibility_status}
              computedAt={match.computed_at}
            />

            {/* Warnings list if any */}
            {match.eligibility_warnings && match.eligibility_warnings.length > 0 && (
              <MatchWarningsList warnings={match.eligibility_warnings} />
            )}

            {/* Seven-Factor Breakdown and Skill Gap */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SevenFactorBreakdown breakdown={match.score_breakdown} />
              <div className="space-y-6">
                <SkillGapCard skillGap={match.skill_gap} />
                <MatchExplanationCard explanation={match.explanation} />
              </div>
            </div>
          </div>
        )}

        {matchError && (
          <div className="p-3.5 rounded-lg border border-rose-500/30 bg-rose-500/10 text-xs text-rose-700 dark:text-rose-400 flex items-center justify-between">
            <span>{matchError}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleEvaluateMatch}
              className="h-7 text-xs border-rose-500/30"
            >
              Retry
            </Button>
          </div>
        )}
      </section>

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
