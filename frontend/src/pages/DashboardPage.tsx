import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Award,
  Bookmark,
  Briefcase,
  CalendarCheck,
  Compass,
  Layers,
  LogIn,
  Sparkles,
  Upload,
} from 'lucide-react'

import { ApplicationCard } from '@/components/applications/ApplicationCard'
import { ApplicationFilters } from '@/components/applications/ApplicationFilters'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { LoadingState } from '@/components/ui/loading-state'
import {
  ApplicationTrackingError,
  deleteApplication,
  listApplications,
  updateApplicationStatus,
} from '@/services/applicationService'
import type {
  ApplicationFilterParams,
  ApplicationResponse,
  ApplicationStatus,
} from '@/types/application'

export function DashboardPage() {
  const [applications, setApplications] = useState<ApplicationResponse[]>([])
  const [totalCount, setTotalCount] = useState<number>(0)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [isUnauthenticated, setIsUnauthenticated] = useState<boolean>(false)

  const [filters, setFilters] = useState<ApplicationFilterParams>({
    status: 'all',
    search: '',
    page: 1,
    page_size: 50,
  })

  // Global counts for all applications
  const [allApps, setAllApps] = useState<ApplicationResponse[]>([])

  const fetchApplications = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    setIsUnauthenticated(false)

    try {
      // 1. Fetch filtered applications for display
      const response = await listApplications(filters)
      setApplications(response.items)
      setTotalCount(response.total)

      // 2. Fetch unfiltered applications to calculate stat cards accurately
      if (filters.status !== 'all' || filters.search) {
        const fullList = await listApplications({ page: 1, page_size: 100 })
        setAllApps(fullList.items)
      } else {
        setAllApps(response.items)
      }
    } catch (err: unknown) {
      if (err instanceof ApplicationTrackingError) {
        if (err.status === 401) {
          setIsUnauthenticated(true)
        } else {
          setError(err.message)
        }
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Failed to load tracked applications. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }, [filters])

  useEffect(() => {
    fetchApplications()
  }, [fetchApplications])

  const handleUpdateStatus = async (
    applicationId: string,
    targetStatus: ApplicationStatus,
    notes?: string
  ): Promise<ApplicationResponse> => {
    const updated = await updateApplicationStatus(applicationId, {
      status: targetStatus,
      notes,
    })
    // Refresh list locally
    setApplications((prev) =>
      prev.map((app) => (app.id === applicationId ? updated : app))
    )
    setAllApps((prev) =>
      prev.map((app) => (app.id === applicationId ? updated : app))
    )
    return updated
  }

  const handleDeleteApplication = async (applicationId: string): Promise<void> => {
    await deleteApplication(applicationId)
    setApplications((prev) => prev.filter((app) => app.id !== applicationId))
    setAllApps((prev) => prev.filter((app) => app.id !== applicationId))
    setTotalCount((prev) => Math.max(0, prev - 1))
  }

  // Derived application stats
  const activeCount = allApps.filter(
    (a) => a.status === 'applied' || a.status === 'oa'
  ).length
  const interviewCount = allApps.filter((a) => a.status === 'interview').length
  const offerCount = allApps.filter((a) => a.status === 'offer').length
  const savedCount = allApps.filter((a) => a.status === 'saved').length

  const stats = [
    {
      label: 'Recommended Matches',
      value: '18',
      change: 'Explore new roles',
      icon: <Sparkles className="h-5 w-5 text-primary" aria-hidden="true" />,
    },
    {
      label: 'Active Applications',
      value: isUnauthenticated ? '0' : String(activeCount),
      change: activeCount === 1 ? '1 in progress' : `${activeCount} in progress`,
      icon: <Briefcase className="h-5 w-5 text-blue-500" aria-hidden="true" />,
    },
    {
      label: 'Interview Pipeline',
      value: isUnauthenticated ? '0' : String(interviewCount),
      change: interviewCount === 1 ? '1 active round' : `${interviewCount} active rounds`,
      icon: <CalendarCheck className="h-5 w-5 text-amber-500" aria-hidden="true" />,
    },
    {
      label: 'Offers Received',
      value: isUnauthenticated ? '0' : String(offerCount),
      change: offerCount === 1 ? '1 offer' : `${offerCount} offers`,
      icon: <Award className="h-5 w-5 text-emerald-500" aria-hidden="true" />,
    },
  ]

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Career Intelligence Dashboard
            </h1>
            <Badge variant="outline" className="text-xs font-medium">
              Live Tracking
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Track and manage your opportunity applications, interview pipelines, and status transitions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/resume">
            <Button size="sm">
              <Upload className="mr-2 h-4 w-4" aria-hidden="true" />
              Upload Resume
            </Button>
          </Link>
          <Link to="/opportunities">
            <Button variant="outline" size="sm">
              <Compass className="mr-2 h-4 w-4" aria-hidden="true" />
              Explore All
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, idx) => (
          <Card key={idx}>
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {stat.label}
              </span>
              <div className="p-2 rounded-lg bg-muted/60">{stat.icon}</div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-extrabold text-foreground">
                {stat.value}
              </div>
              <p className="text-xs text-muted-foreground mt-1 flex items-center">
                {stat.change}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Tracked Applications Section */}
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
              <Layers className="h-5 w-5 text-primary" aria-hidden="true" />
              Application Pipeline & Status Transitions
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Review saved and submitted applications with strict lifecycle transitions.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              <Bookmark className="mr-1 h-3 w-3" aria-hidden="true" />
              {savedCount} Saved
            </Badge>
          </div>
        </div>

        {/* Unauthenticated State */}
        {isUnauthenticated && (
          <Card className="border-border">
            <CardContent className="p-8 text-center space-y-4">
              <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                <LogIn className="h-6 w-6" aria-hidden="true" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <CardTitle className="text-lg">Sign In to Track Applications</CardTitle>
                <CardDescription className="text-xs">
                  Create an account or sign in to save opportunities, track application statuses, and manage your job search pipeline.
                </CardDescription>
              </div>
              <div className="flex items-center justify-center gap-3 pt-2">
                <Link to="/login">
                  <Button size="sm">
                    <LogIn className="mr-2 h-4 w-4" aria-hidden="true" />
                    Sign In
                  </Button>
                </Link>
                <Link to="/opportunities">
                  <Button variant="outline" size="sm">
                    Browse Opportunities
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Authenticated State */}
        {!isUnauthenticated && (
          <>
            {/* Filters */}
            <ApplicationFilters
              filters={filters}
              onFilterChange={setFilters}
              totalCount={totalCount}
            />

            {/* Loading */}
            {isLoading && (
              <LoadingState message="Loading your tracked applications..." />
            )}

            {/* Error */}
            {!isLoading && error && (
              <ErrorState
                title="Could not load applications"
                description={error}
                onRetry={fetchApplications}
                retryLabel="Retry"
              />
            )}

            {/* Empty States */}
            {!isLoading && !error && applications.length === 0 && (
              <>
                {filters.status !== 'all' || Boolean(filters.search?.trim()) ? (
                  <EmptyState
                    title="No matching applications"
                    description="No tracked applications match your current status or keyword filter."
                    actionLabel="Reset Filters"
                    onAction={() =>
                      setFilters({ status: 'all', search: '', page: 1, page_size: 50 })
                    }
                    className="p-8"
                  />
                ) : (
                  <EmptyState
                    title="No applications tracked yet"
                    description="You haven't saved or applied to any opportunities yet. Browse recommended opportunities to begin tracking your applications."
                    actionLabel="Explore Opportunities"
                    onAction={() => {
                      window.location.href = '/opportunities'
                    }}
                    className="p-8"
                  />
                )}
              </>
            )}

            {/* Applications List */}
            {!isLoading && !error && applications.length > 0 && (
              <div className="space-y-4">
                {applications.map((app) => (
                  <ApplicationCard
                    key={app.id}
                    application={app}
                    onUpdateStatus={handleUpdateStatus}
                    onDeleteApplication={handleDeleteApplication}
                    onRefresh={fetchApplications}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
