/**
 * RecommendationsPage for Phase 20.
 * Provides personalized opportunity recommendations and hybrid match evaluation.
 *
 * Implements:
 * - Semantic Discovery View (GET /api/v1/recommendations/)
 * - Evaluated Matches View (GET /api/v1/matches/ with status & min_score filters)
 * - On-demand Batch Evaluation (POST /api/v1/matches/evaluate)
 * - Seven-factor score breakdown, eligibility status, and skill gap visualization
 * - Mandatory ranking-aid disclaimers
 * - Robust error handling (400, 401, 404, 500) and retry states
 */

import * as React from 'react'
import { Link } from 'react-router-dom'
import {
  Compass,
  FileText,
  Info,
  LogIn,
  RefreshCw,
  Sparkles,
  Target,
  UserCheck,
  UserPlus,
} from 'lucide-react'

import { EligibilityBadge } from '@/components/matching/EligibilityBadge'
import { MatchExplanationCard } from '@/components/matching/MatchExplanationCard'
import { MatchScoreCard } from '@/components/matching/MatchScoreCard'
import { MatchWarningsList } from '@/components/matching/MatchWarningsList'
import { SevenFactorBreakdown } from '@/components/matching/SevenFactorBreakdown'
import { SkillGapCard } from '@/components/matching/SkillGapCard'
import { RecommendationCard } from '@/components/recommendations/RecommendationCard'
import { RecommendationFilters } from '@/components/recommendations/RecommendationFilters'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { LoadingState } from '@/components/ui/loading-state'
import {
  evaluateMatches,
  getMatchByOpportunityId,
  listMatches,
  triggerMatch,
} from '@/services/matchingService'
import { getRecommendations, RecommendationError } from '@/services/recommendationService'
import type {
  EligibilityStatus,
  MatchFilterParams,
  MatchResponse,
  MatchSummaryResponse,
} from '@/types/matching'
import type {
  RecommendationFilterParams,
  SemanticOpportunityItem,
} from '@/types/recommendation'

export function RecommendationsPage() {
  const [activeTab, setActiveTab] = React.useState<'semantic' | 'matches'>('semantic')

  // Semantic Recommendations State
  const [items, setItems] = React.useState<SemanticOpportunityItem[]>([])
  const [total, setTotal] = React.useState(0)
  const [totalPages, setTotalPages] = React.useState(0)
  const [loading, setLoading] = React.useState(true)
  const [errorStatus, setErrorStatus] = React.useState<number | null>(null)
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)

  // Evaluated Match Summaries Cache (by opportunity_id)
  const [matchesMap, setMatchesMap] = React.useState<Record<string, MatchSummaryResponse>>({})
  const [batchEvaluating, setBatchEvaluating] = React.useState(false)
  const [evaluatingId, setEvaluatingId] = React.useState<string | null>(null)

  // Matches Tab State (persisted match records)
  const [evaluatedMatches, setEvaluatedMatches] = React.useState<MatchSummaryResponse[]>([])
  const [matchesTotal, setMatchesTotal] = React.useState(0)
  const [matchesTotalPages, setMatchesTotalPages] = React.useState(0)
  const [matchesLoading, setMatchesLoading] = React.useState(false)
  const [matchesError, setMatchesError] = React.useState<string | null>(null)

  const [matchFilters, setMatchFilters] = React.useState<MatchFilterParams>({
    page: 1,
    page_size: 12,
    eligibility_status: '',
    min_score: '',
  })

  // Selected match for detailed breakdown inspection modal/panel
  const [selectedMatch, setSelectedMatch] = React.useState<MatchResponse | null>(null)
  const [inspectLoading, setInspectLoading] = React.useState(false)

  const [filters, setFilters] = React.useState<RecommendationFilterParams>({
    page: 1,
    page_size: 12,
    opportunity_type: '',
    work_mode: '',
    employment_type: '',
    location: '',
  })

  // Fetch semantic recommendations
  const fetchRecommendations = React.useCallback(async (params: RecommendationFilterParams) => {
    setLoading(true)
    setErrorStatus(null)
    setErrorMessage(null)

    try {
      const data = await getRecommendations(params)
      setItems(data.items)
      setTotal(data.total)
      setTotalPages(data.total_pages)

      // If user is authenticated, query existing matches for visible opportunities
      const token = localStorage.getItem('access_token')
      if (token && data.items.length > 0) {
        try {
          const matchList = await listMatches({ page: 1, page_size: 100 }, token)
          const map: Record<string, MatchSummaryResponse> = {}
          for (const m of matchList.items) {
            map[m.opportunity_id] = m
          }
          setMatchesMap((prev) => ({ ...prev, ...map }))
        } catch {
          // Non-blocking: background match cache fetch
        }
      }
    } catch (err: unknown) {
      if (err instanceof RecommendationError) {
        setErrorStatus(err.status)
        setErrorMessage(err.message)
      } else if (err instanceof Error) {
        setErrorMessage(err.message)
      } else {
        setErrorMessage('Failed to load recommendations. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch evaluated matches for the matches tab
  const fetchEvaluatedMatches = React.useCallback(async (params: MatchFilterParams) => {
    const token = localStorage.getItem('access_token')
    if (!token) return

    setMatchesLoading(true)
    setMatchesError(null)
    try {
      const data = await listMatches(params, token)
      setEvaluatedMatches(data.items)
      setMatchesTotal(data.total)
      setMatchesTotalPages(data.total_pages)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load evaluated matches.'
      setMatchesError(msg)
    } finally {
      setMatchesLoading(false)
    }
  }, [])

  // Debounce location search, immediately trigger other filters
  React.useEffect(() => {
    const timer = setTimeout(() => {
      fetchRecommendations(filters)
    }, 300)

    return () => clearTimeout(timer)
  }, [filters, fetchRecommendations])

  // Trigger matches fetch when tab switches to 'matches'
  React.useEffect(() => {
    if (activeTab === 'matches') {
      fetchEvaluatedMatches(matchFilters)
    }
  }, [activeTab, matchFilters, fetchEvaluatedMatches])

  const handleFilterChange = (newFilters: Partial<RecommendationFilterParams>) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
      page: newFilters.page ?? 1,
    }))
  }

  const handleResetFilters = () => {
    setFilters({
      page: 1,
      page_size: 12,
      opportunity_type: '',
      work_mode: '',
      employment_type: '',
      location: '',
    })
  }

  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || newPage > totalPages) return
    handleFilterChange({ page: newPage })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Trigger batch evaluation for visible recommendations
  const handleBatchEvaluate = async () => {
    if (items.length === 0) return
    setBatchEvaluating(true)
    try {
      const oppIds = items.map((i) => i.id)
      const res = await evaluateMatches({ opportunity_ids: oppIds, limit: oppIds.length })
      const newMap = { ...matchesMap }
      for (const m of res.items) {
        newMap[m.opportunity_id] = m
      }
      setMatchesMap(newMap)
    } catch {
      // Handled gracefully
    } finally {
      setBatchEvaluating(false)
    }
  }

  // Trigger single evaluation
  const handleEvaluateSingle = async (opportunityId: string, semanticSimilarity?: number) => {
    setEvaluatingId(opportunityId)
    try {
      const result = await triggerMatch(opportunityId, semanticSimilarity)
      const summary: MatchSummaryResponse = {
        id: result.id,
        candidate_profile_id: result.candidate_profile_id,
        opportunity_id: result.opportunity_id,
        semantic_score: result.semantic_score,
        deterministic_score: result.deterministic_score,
        final_score: result.final_score,
        eligibility_status: result.eligibility_status,
        eligibility_warnings: result.eligibility_warnings,
        computed_at: result.computed_at,
      }
      setMatchesMap((prev) => ({ ...prev, [opportunityId]: summary }))
    } catch {
      // Handled gracefully
    } finally {
      setEvaluatingId(null)
    }
  }

  // Inspect full breakdown
  const handleInspectMatch = async (opportunityId: string) => {
    setInspectLoading(true)
    try {
      const fullMatch = await getMatchByOpportunityId(opportunityId)
      setSelectedMatch(fullMatch)
    } catch {
      // Handled gracefully
    } finally {
      setInspectLoading(false)
    }
  }

  return (
    <div className="space-y-6 sm:space-y-8 pb-16">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border/60 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              AI Semantic Retrieval
            </span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-foreground sm:text-4xl">
            Personalized Recommendations
          </h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-3xl leading-relaxed">
            Opportunities ranked by dense semantic vector similarity to your professional profile and resume.
            Scores reflect text alignment and content relevance without evaluating hiring probability or strict requirements.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto shrink-0 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchRecommendations(filters)}
            disabled={loading}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Link to="/profile">
            <Button variant="default" size="sm" className="flex items-center gap-1.5">
              <UserCheck className="h-3.5 w-3.5" />
              Edit Profile
            </Button>
          </Link>
        </div>
      </div>

      {/* Ranking Aid Mandatory Disclaimer */}
      <div
        className="flex items-start gap-2.5 p-3.5 rounded-xl bg-muted/40 border border-border/70 text-xs text-muted-foreground"
        role="note"
      >
        <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" aria-hidden="true" />
        <p className="leading-relaxed">
          <strong className="text-foreground font-semibold">Ranking Aid Disclaimer:</strong> Match
          scores and semantic recommendations are ranking aids designed to help you prioritize opportunities.
          They are not a guarantee of job suitability, interview selection, or hiring decisions.
        </p>
      </div>

      {/* View Switcher: Semantic Recommendations vs Evaluated Matches */}
      {errorStatus !== 401 && errorStatus !== 404 && errorStatus !== 400 && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border/60 pb-3">
          <div className="inline-flex rounded-lg border border-border p-1 bg-muted/40 text-xs font-medium">
            <button
              type="button"
              onClick={() => setActiveTab('semantic')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                activeTab === 'semantic'
                  ? 'bg-background text-foreground shadow-sm font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Semantic Recommendations ({total})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('matches')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                activeTab === 'matches'
                  ? 'bg-background text-foreground shadow-sm font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Evaluated Matches ({Object.keys(matchesMap).length > 0 ? Object.keys(matchesMap).length : matchesTotal})
            </button>
          </div>

          {activeTab === 'semantic' && items.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleBatchEvaluate}
              disabled={batchEvaluating || loading}
              className="text-xs self-start sm:self-auto"
            >
              <Target className={`mr-1.5 h-3.5 w-3.5 ${batchEvaluating ? 'animate-spin' : ''}`} />
              {batchEvaluating ? 'Evaluating...' : 'Evaluate All Visible Matches'}
            </Button>
          )}
        </div>
      )}

      {/* Main Content Area */}
      {loading && activeTab === 'semantic' ? (
        <div className="space-y-4">
          <LoadingState message="Finding your best opportunities..." />
        </div>
      ) : errorStatus === 401 ? (
        /* 401 Unauthorized State */
        <Card className="max-w-lg mx-auto text-center border-border shadow-sm">
          <CardHeader>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary mb-2">
              <LogIn className="h-6 w-6" aria-hidden="true" />
            </div>
            <CardTitle className="text-xl">Authentication Required</CardTitle>
            <CardDescription>
              Personalized recommendations require an authenticated candidate session.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {errorMessage || 'Please sign in to view recommendations tailored to your profile.'}
          </CardContent>
          <CardFooter className="justify-center">
            <Link to="/login">
              <Button className="flex items-center gap-2">
                <LogIn className="h-4 w-4" />
                Sign In to CareerLens
              </Button>
            </Link>
          </CardFooter>
        </Card>
      ) : errorStatus === 404 ? (
        /* 404 Profile Not Found State */
        <Card className="max-w-lg mx-auto text-center border-border shadow-sm">
          <CardHeader>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 mb-2">
              <UserPlus className="h-6 w-6" aria-hidden="true" />
            </div>
            <CardTitle className="text-xl">Candidate Profile Required</CardTitle>
            <CardDescription>
              We couldn't find a candidate profile for your account.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground leading-relaxed">
            {errorMessage ||
              'A candidate profile is needed to generate dense vector embeddings for semantic matching.'}
          </CardContent>
          <CardFooter className="justify-center">
            <Link to="/profile">
              <Button className="flex items-center gap-2">
                <UserPlus className="h-4 w-4" />
                Create Candidate Profile
              </Button>
            </Link>
          </CardFooter>
        </Card>
      ) : errorStatus === 400 ? (
        /* 400 Insufficient Profile Content State */
        <Card className="max-w-lg mx-auto text-center border-border shadow-sm">
          <CardHeader>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 mb-2">
              <FileText className="h-6 w-6" aria-hidden="true" />
            </div>
            <CardTitle className="text-xl">Profile Details Needed</CardTitle>
            <CardDescription>
              Your candidate profile has insufficient content for vector recommendations.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground leading-relaxed">
            {errorMessage ||
              'Please add skills, experience, or headline to your profile so our semantic pipeline can index your background.'}
          </CardContent>
          <CardFooter className="justify-center gap-3">
            <Link to="/profile">
              <Button className="flex items-center gap-2">
                <UserCheck className="h-4 w-4" />
                Update Profile Skills
              </Button>
            </Link>
            <Link to="/resume">
              <Button variant="outline" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Upload Resume
              </Button>
            </Link>
          </CardFooter>
        </Card>
      ) : errorMessage ? (
        /* Generic / 500 Network or Server Error State */
        <ErrorState
          title="Unable to load recommendations"
          description={errorMessage}
          onRetry={() => fetchRecommendations(filters)}
        />
      ) : activeTab === 'semantic' ? (
        /* Semantic Tab Content */
        <div className="space-y-6">
          <RecommendationFilters
            filters={filters}
            onFilterChange={handleFilterChange}
            onReset={handleResetFilters}
            totalCount={total}
          />

          {items.length === 0 ? (
            <EmptyState
              icon={<Compass className="h-6 w-6" />}
              title="No recommendations match your filters"
              description="Try broadening your work mode, employment type, or location filters to see more semantically relevant opportunities."
              actionLabel="Reset All Filters"
              onAction={handleResetFilters}
            />
          ) : (
            <div className="space-y-6">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span aria-live="polite">
                  Showing {items.length} of {total} recommendations (Ranked by semantic vector alignment)
                </span>
                <span>
                  Page {filters.page} of {totalPages}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {items.map((item) => (
                  <RecommendationCard
                    key={item.id}
                    item={item}
                    matchSummary={matchesMap[item.id]}
                    onEvaluate={handleEvaluateSingle}
                    isEvaluating={evaluatingId === item.id}
                  />
                ))}
              </div>

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-6 border-t border-border/60">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange((filters.page || 1) - 1)}
                    disabled={(filters.page || 1) <= 1}
                  >
                    Previous
                  </Button>

                  <span className="text-xs text-muted-foreground px-3">
                    Page {filters.page} of {totalPages}
                  </span>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange((filters.page || 1) + 1)}
                    disabled={(filters.page || 1) >= totalPages}
                  >
                    Next
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        /* Evaluated Matches Tab Content */
        <div className="space-y-6">
          {/* Match Filters */}
          <div className="rounded-xl border border-border bg-card p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs">
            <div className="flex items-center gap-3 flex-wrap">
              <label htmlFor="eligibility-status-select" className="font-medium text-foreground">
                Eligibility Status:
              </label>
              <select
                id="eligibility-status-select"
                aria-label="Filter by eligibility status"
                value={matchFilters.eligibility_status || ''}
                onChange={(e) =>
                  setMatchFilters((prev) => ({
                    ...prev,
                    eligibility_status: e.target.value as EligibilityStatus | '',
                    page: 1,
                  }))
                }
                className="rounded-md border border-input bg-background px-3 py-1.5 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="">All Statuses</option>
                <option value="eligible">Eligible</option>
                <option value="partial">Partial</option>
                <option value="review_required">Review Required</option>
              </select>

              <label htmlFor="min-score-input" className="font-medium text-foreground ml-2">
                Min Score:
              </label>
              <input
                id="min-score-input"
                aria-label="Filter by minimum match score"
                type="number"
                step="0.05"
                min="0"
                max="1"
                placeholder="e.g. 0.5"
                value={matchFilters.min_score !== undefined ? matchFilters.min_score : ''}
                onChange={(e) =>
                  setMatchFilters((prev) => ({
                    ...prev,
                    min_score: e.target.value === '' ? '' : parseFloat(e.target.value),
                    page: 1,
                  }))
                }
                className="w-24 rounded-md border border-input bg-background px-2.5 py-1.5 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setMatchFilters({
                  page: 1,
                  page_size: 12,
                  eligibility_status: '',
                  min_score: '',
                })
              }
              className="h-8 text-xs"
            >
              Reset Filters
            </Button>
          </div>

          {/* Evaluated Matches Grid */}
          {matchesLoading ? (
            <LoadingState message="Loading evaluated matches..." />
          ) : matchesError ? (
            <ErrorState
              title="Unable to load matches"
              description={matchesError}
              onRetry={() => fetchEvaluatedMatches(matchFilters)}
            />
          ) : evaluatedMatches.length === 0 ? (
            <EmptyState
              icon={<Target className="h-6 w-6" />}
              title="No evaluated matches found"
              description="You have not evaluated any opportunities matching these criteria yet. Evaluate recommendations or browse opportunities to compute match scores."
              actionLabel="Explore Opportunities"
              onAction={() => setActiveTab('semantic')}
            />
          ) : (
            <div className="space-y-6">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>
                  Showing {evaluatedMatches.length} of {matchesTotal} evaluated matches
                </span>
                {matchesTotalPages > 1 && (
                  <span>
                    Page {matchFilters.page} of {matchesTotalPages}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {evaluatedMatches.map((matchItem) => (
                  <Card key={matchItem.id} className="flex flex-col h-full hover:border-primary/50 transition-colors">
                    <CardHeader className="pb-3 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xl font-extrabold text-foreground">
                          {Math.round(matchItem.final_score * 100)}%
                        </span>
                        <EligibilityBadge status={matchItem.eligibility_status} />
                      </div>
                      <CardTitle className="text-sm font-semibold text-muted-foreground">
                        Opportunity: {matchItem.opportunity_id}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 pb-4 space-y-2 text-xs text-muted-foreground">
                      <div className="flex justify-between py-1 border-b border-border/40">
                        <span>Semantic Score:</span>
                        <span className="font-semibold text-foreground">
                          {Math.round(matchItem.semantic_score * 100)}%
                        </span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-border/40">
                        <span>Deterministic Score:</span>
                        <span className="font-semibold text-foreground">
                          {Math.round(matchItem.deterministic_score * 100)}%
                        </span>
                      </div>
                      {matchItem.eligibility_warnings && matchItem.eligibility_warnings.length > 0 && (
                        <div className="text-[11px] text-amber-600 dark:text-amber-400 bg-amber-500/10 p-2 rounded">
                          {matchItem.eligibility_warnings.length} warning(s) flagged
                        </div>
                      )}
                    </CardContent>
                    <CardFooter className="pt-2 border-t border-border/60 flex items-center justify-between text-xs">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleInspectMatch(matchItem.opportunity_id)}
                        className="h-7 text-xs px-2"
                      >
                        Inspect Breakdown
                      </Button>
                      <Link
                        to={`/opportunities/${matchItem.opportunity_id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        Opportunity Details &rarr;
                      </Link>
                    </CardFooter>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Inspect Match Detail Drawer/Modal */}
      {selectedMatch && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="inspect-match-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm"
        >
          <div className="bg-card border border-border rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div>
                <h2 id="inspect-match-title" className="text-lg font-bold text-foreground">
                  Match Evaluation Breakdown
                </h2>
                <p className="text-xs text-muted-foreground">
                  Detailed seven-factor scores and skill gap analysis
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedMatch(null)}
              >
                Close
              </Button>
            </div>

            <MatchScoreCard
              finalScore={selectedMatch.final_score}
              semanticScore={selectedMatch.semantic_score}
              deterministicScore={selectedMatch.deterministic_score}
              eligibilityStatus={selectedMatch.eligibility_status}
              computedAt={selectedMatch.computed_at}
            />

            {selectedMatch.eligibility_warnings && selectedMatch.eligibility_warnings.length > 0 && (
              <MatchWarningsList warnings={selectedMatch.eligibility_warnings} />
            )}

            <SevenFactorBreakdown breakdown={selectedMatch.score_breakdown} />
            <SkillGapCard skillGap={selectedMatch.skill_gap} />
            <MatchExplanationCard explanation={selectedMatch.explanation} />

            <div className="flex justify-end pt-3 border-t border-border/60">
              <Button onClick={() => setSelectedMatch(null)}>
                Done
              </Button>
            </div>
          </div>
        </div>
      )}

      {inspectLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/50">
          <LoadingState message="Loading match details..." />
        </div>
      )}
    </div>
  )
}
