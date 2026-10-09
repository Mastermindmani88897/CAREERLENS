/**
 * RecommendationFilters component for Phase 18.
 * Provides facet controls for the parameters supported by the backend:
 * - opportunity_type: 'job' | 'internship' | 'hackathon'
 * - work_mode: 'remote' | 'hybrid' | 'onsite' | 'any'
 * - employment_type: 'fulltime' | 'parttime' | 'internship' | 'contract' | 'any'
 * - location: string (substring filter)
 */

import { X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { OpportunityType, WorkMode, EmploymentType } from '@/types/opportunity'
import type { RecommendationFilterParams } from '@/types/recommendation'

interface RecommendationFiltersProps {
  filters: RecommendationFilterParams
  onFilterChange: (newFilters: Partial<RecommendationFilterParams>) => void
  onReset: () => void
  totalCount: number
}

export function RecommendationFilters({
  filters,
  onFilterChange,
  onReset,
  totalCount,
}: RecommendationFiltersProps) {
  const hasActiveFilters = Boolean(
    filters.opportunity_type ||
      filters.work_mode ||
      filters.employment_type ||
      filters.location
  )

  return (
    <div className="space-y-4 rounded-xl border border-border bg-card/60 p-4 sm:p-5">
      {/* Opportunity Type Pill Buttons */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-muted-foreground mr-1">Opportunity Type:</span>
        {[
          { label: 'All Opportunities', value: '' },
          { label: 'Jobs', value: 'job' },
          { label: 'Internships', value: 'internship' },
          { label: 'Hackathons', value: 'hackathon' },
        ].map((item) => {
          const isSelected = (filters.opportunity_type || '') === item.value
          return (
            <button
              key={item.label}
              type="button"
              onClick={() =>
                onFilterChange({
                  opportunity_type: item.value as OpportunityType | '',
                  page: 1,
                })
              }
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                isSelected
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              {item.label}
            </button>
          )
        })}
      </div>

      {/* Multi-Facet Grid: Work Mode, Employment Type, Location */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-border/50">
        {/* Work Mode */}
        <div>
          <label
            htmlFor="recommendation-work-mode-select"
            className="block text-xs font-medium text-muted-foreground mb-1"
          >
            Work Mode
          </label>
          <select
            id="recommendation-work-mode-select"
            value={filters.work_mode || ''}
            onChange={(e) =>
              onFilterChange({
                work_mode: e.target.value as WorkMode | '',
                page: 1,
              })
            }
            className="w-full h-8 rounded-md border border-input bg-background px-2.5 py-1 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">All Work Modes</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">Onsite</option>
            <option value="any">Any Work Mode</option>
          </select>
        </div>

        {/* Employment Type */}
        <div>
          <label
            htmlFor="recommendation-employment-type-select"
            className="block text-xs font-medium text-muted-foreground mb-1"
          >
            Employment Type
          </label>
          <select
            id="recommendation-employment-type-select"
            value={filters.employment_type || ''}
            onChange={(e) =>
              onFilterChange({
                employment_type: e.target.value as EmploymentType | '',
                page: 1,
              })
            }
            className="w-full h-8 rounded-md border border-input bg-background px-2.5 py-1 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">All Employment Types</option>
            <option value="fulltime">Full-time</option>
            <option value="parttime">Part-time</option>
            <option value="internship">Internship</option>
            <option value="contract">Contract</option>
            <option value="any">Any Employment</option>
          </select>
        </div>

        {/* Location Filter */}
        <div>
          <label
            htmlFor="recommendation-location-input"
            className="block text-xs font-medium text-muted-foreground mb-1"
          >
            Location
          </label>
          <Input
            id="recommendation-location-input"
            type="text"
            placeholder="e.g. San Francisco, London"
            value={filters.location || ''}
            onChange={(e) => onFilterChange({ location: e.target.value, page: 1 })}
            className="h-8 text-xs bg-background"
          />
        </div>
      </div>

      {/* Active Filter Indicators & Clear Action */}
      {hasActiveFilters && (
        <div className="flex items-center justify-between pt-2 border-t border-border/40 text-xs">
          <span className="text-muted-foreground">
            Filters applied ({totalCount} matching {totalCount === 1 ? 'recommendation' : 'recommendations'})
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            className="h-7 text-xs text-muted-foreground hover:text-foreground"
          >
            <X className="mr-1 h-3.5 w-3.5" />
            Clear all filters
          </Button>
        </div>
      )}
    </div>
  )
}
