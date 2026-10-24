import React from 'react'
import { Filter, RotateCcw, Search } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  APPLICATION_STATUS_LABELS,
  type ApplicationFilterParams,
  type ApplicationStatus,
} from '@/types/application'

interface ApplicationFiltersProps {
  filters: ApplicationFilterParams
  onFilterChange: (newFilters: ApplicationFilterParams) => void
  totalCount: number
}

const STATUS_OPTIONS: { label: string; value: ApplicationStatus | 'all' }[] = [
  { label: 'All Applications', value: 'all' },
  { label: APPLICATION_STATUS_LABELS.saved, value: 'saved' },
  { label: APPLICATION_STATUS_LABELS.applied, value: 'applied' },
  { label: APPLICATION_STATUS_LABELS.oa, value: 'oa' },
  { label: APPLICATION_STATUS_LABELS.interview, value: 'interview' },
  { label: APPLICATION_STATUS_LABELS.offer, value: 'offer' },
  { label: APPLICATION_STATUS_LABELS.rejected, value: 'rejected' },
  { label: APPLICATION_STATUS_LABELS.withdrawn, value: 'withdrawn' },
]

export function ApplicationFilters({
  filters,
  onFilterChange,
  totalCount,
}: ApplicationFiltersProps) {
  const currentStatus = filters.status || 'all'
  const currentSearch = filters.search || ''

  const handleStatusChange = (status: ApplicationStatus | 'all') => {
    onFilterChange({
      ...filters,
      status,
      page: 1,
    })
  }

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filters,
      search: e.target.value,
      page: 1,
    })
  }

  const handleReset = () => {
    onFilterChange({
      status: 'all',
      search: '',
      page: 1,
    })
  }

  const hasActiveFilters = currentStatus !== 'all' || Boolean(currentSearch.trim())

  return (
    <div className="space-y-4 bg-card p-4 rounded-xl border border-border">
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        {/* Search input */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <Input
            type="search"
            placeholder="Search by job title, company, or location..."
            value={currentSearch}
            onChange={handleSearchChange}
            className="pl-9 text-xs"
            aria-label="Search applications"
          />
        </div>

        {/* Counter & Reset */}
        <div className="flex items-center gap-2 justify-between sm:justify-end shrink-0">
          <span className="text-xs text-muted-foreground font-medium">
            <span className="text-foreground font-bold">{`${totalCount} application${totalCount === 1 ? '' : 's'}`}</span>
          </span>
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              className="text-xs h-8 px-2 text-muted-foreground hover:text-foreground"
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
              Reset
            </Button>
          )}
        </div>
      </div>

      {/* Status Filter Pills */}
      <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-border/60">
        <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mr-1 flex items-center">
          <Filter className="h-3 w-3 mr-1" aria-hidden="true" />
          Status:
        </span>
        {STATUS_OPTIONS.map((opt) => {
          const isActive = currentStatus === opt.value
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => handleStatusChange(opt.value)}
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                isActive
                  ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                  : 'bg-muted/70 hover:bg-muted text-muted-foreground hover:text-foreground'
              }`}
              aria-pressed={isActive}
            >
              {opt.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
