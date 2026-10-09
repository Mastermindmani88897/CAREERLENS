/**
 * RecommendationsPage for Phase 18.
 * Provides personalized, semantically ranked opportunity recommendations
 * based on candidate dense vector alignment.
 *
 * Implements states for:
 * - Loading skeletons (LoadingState)
 * - Empty results (EmptyState)
 * - 404: Profile not found (CTA to /profile)
 * - 400: Insufficient profile content (CTA to /profile)
 * - 401: Unauthorized (CTA to /login)
 * - 500 / Network errors (ErrorState with retry)
 * - Filtering and pagination
 */

import * as React from 'react'
import { Link } from 'react-router-dom'
import { Compass, RefreshCw, Sparkles, UserCheck, UserPlus, LogIn, FileText } from 'lucide-react'

import { RecommendationCard } from '@/components/recommendations/RecommendationCard'
import { RecommendationFilters } from '@/components/recommendations/RecommendationFilters'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { LoadingState } from '@/components/ui/loading-state'
import { getRecommendations, RecommendationError } from '@/services/recommendationService'
import type {
  RecommendationFilterParams,
  SemanticOpportunityItem,
} from '@/types/recommendation'

export function RecommendationsPage() {
  const [items, setItems] = React.useState<SemanticOpportunityItem[]>([])
  const [total, setTotal] = React.useState(0)
  const [totalPages, setTotalPages] = React.useState(0)
  const [loading, setLoading] = React.useState(true)
  const [errorStatus, setErrorStatus] = React.useState<number | null>(null)
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)

  const [filters, setFilters] = React.useState<RecommendationFilterParams>({
    page: 1,
    page_size: 12,
    opportunity_type: '',
    work_mode: '',
    employment_type: '',
    location: '',
  })

  const fetchRecommendations = React.useCallback(async (params: RecommendationFilterParams) => {
    setLoading(true)
    setErrorStatus(null)
    setErrorMessage(null)

    try {
      const data = await getRecommendations(params)
      setItems(data.items)
      setTotal(data.total)
      setTotalPages(data.total_pages)
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

  // Debounce location search, immediately trigger other filters
  React.useEffect(() => {
    const timer = setTimeout(() => {
      fetchRecommendations(filters)
    }, 300)

    return () => clearTimeout(timer)
  }, [filters, fetchRecommendations])

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

  return (
    <div className="space-y-6 sm:space-y-8">
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

        <div className="flex items-center gap-2 self-start md:self-auto shrink-0">
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

      {/* Filter Controls (Shown only if not in blocking profile/auth error state) */}
      {errorStatus !== 401 && errorStatus !== 404 && errorStatus !== 400 && (
        <RecommendationFilters
          filters={filters}
          onFilterChange={handleFilterChange}
          onReset={handleResetFilters}
          totalCount={total}
        />
      )}

      {/* Main Content Area */}
      {loading ? (
        <div className="space-y-4">
          <LoadingState
            message="Finding your best opportunities..."
          />
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
      ) : items.length === 0 ? (
        /* 200 OK with Empty Items State */
        <EmptyState
          icon={<Compass className="h-6 w-6" />}
          title="No recommendations match your filters"
          description="Try broadening your work mode, employment type, or location filters to see more semantically relevant opportunities."
          actionLabel="Reset All Filters"
          onAction={handleResetFilters}
        />
      ) : (
        /* Successful Results Grid */
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
              <RecommendationCard key={item.id} item={item} />
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
  )
}
