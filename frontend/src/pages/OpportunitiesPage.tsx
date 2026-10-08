/**
 * OpportunitiesPage for Phase 15.
 * Core opportunity discovery view with search, filtering, grid layout,
 * loading skeletons, empty state, error state, and pagination.
 */

import * as React from 'react'
import { Compass, RefreshCw } from 'lucide-react'

import { OpportunityCard } from '@/components/opportunities/OpportunityCard'
import { OpportunityFilters } from '@/components/opportunities/OpportunityFilters'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { LoadingState } from '@/components/ui/loading-state'
import { getOpportunities } from '@/services/opportunityService'
import type {
  Opportunity,
  OpportunityFilterParams,
} from '@/types/opportunity'

export function OpportunitiesPage() {
  const [opportunities, setOpportunities] = React.useState<Opportunity[]>([])
  const [total, setTotal] = React.useState(0)
  const [totalPages, setTotalPages] = React.useState(0)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  const [filters, setFilters] = React.useState<OpportunityFilterParams>({
    page: 1,
    page_size: 12,
    sort_by: 'newest',
    opportunity_type: '',
    work_mode: '',
    employment_type: '',
    location: '',
    min_experience_years: '',
    max_experience_years: '',
    keyword: '',
  })

  // Debounced search / filter fetch
  const fetchOpportunities = React.useCallback(async (params: OpportunityFilterParams) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getOpportunities(params)
      setOpportunities(data.items)
      setTotal(data.total)
      setTotalPages(data.total_pages)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load opportunities.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  // Debounce keyword search by 300ms, immediately trigger other filters
  React.useEffect(() => {
    const handler = setTimeout(() => {
      fetchOpportunities(filters)
    }, 300)

    return () => clearTimeout(handler)
  }, [filters, fetchOpportunities])

  const handleFilterChange = (newFilters: Partial<OpportunityFilterParams>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
  }

  const handleResetFilters = () => {
    setFilters({
      page: 1,
      page_size: 12,
      sort_by: 'newest',
      opportunity_type: '',
      work_mode: '',
      employment_type: '',
      location: '',
      min_experience_years: '',
      max_experience_years: '',
      keyword: '',
    })
  }

  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || newPage > totalPages) return
    handleFilterChange({ page: newPage })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/80 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Compass className="h-4 w-4" aria-hidden="true" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Opportunity Discovery
            </h1>
          </div>
          <p className="text-sm text-muted-foreground">
            Explore curated jobs, internships, and hackathons tailored for software and tech talent.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchOpportunities(filters)}
          disabled={loading}
          className="self-start sm:self-auto"
        >
          <RefreshCw className={`mr-2 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <OpportunityFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={handleResetFilters}
        totalCount={total}
      />

      {/* Main Content Area */}
      {loading ? (
        <div className="py-16">
          <LoadingState message="Discovering opportunities..." />
        </div>
      ) : error ? (
        <ErrorState
          title="Could not load opportunities"
          description={error}
          onRetry={() => fetchOpportunities(filters)}
        />
      ) : opportunities.length === 0 ? (
        <EmptyState
          title="No matching opportunities found"
          description="Try broadening your search term or clearing some filters to explore more options."
          actionLabel="Clear all filters"
          onAction={handleResetFilters}
        />
      ) : (
        <div className="space-y-6">
          {/* Results Summary */}
          <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
            <span>
              Showing {opportunities.length} of {total} {total === 1 ? 'result' : 'results'}
            </span>
            {totalPages > 1 && (
              <span>
                Page {filters.page} of {totalPages}
              </span>
            )}
          </div>

          {/* Opportunities Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {opportunities.map((opp) => (
              <OpportunityCard key={opp.id} opportunity={opp} />
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

              <div className="flex items-center gap-1 px-2 text-xs font-medium text-muted-foreground">
                Page {filters.page || 1} of {totalPages}
              </div>

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
