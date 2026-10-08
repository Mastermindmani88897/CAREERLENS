/**
 * OpportunityFilters component for Phase 15.
 * Provides controls for opportunity type, work mode, employment type, location,
 * experience interval presets, sorting, and reset action.
 */

import { Search, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type {
  OpportunityFilterParams,
  OpportunitySortBy,
  OpportunityType,
  WorkMode,
} from '@/types/opportunity'

interface OpportunityFiltersProps {
  filters: OpportunityFilterParams
  onFilterChange: (newFilters: Partial<OpportunityFilterParams>) => void
  onReset: () => void
  totalCount: number
}

export function OpportunityFilters({
  filters,
  onFilterChange,
  onReset,
  totalCount,
}: OpportunityFiltersProps) {
  // Experience presets matching interval overlap semantics
  const handleExperiencePreset = (preset: string) => {
    switch (preset) {
      case 'entry':
        onFilterChange({ min_experience_years: 0, max_experience_years: 2 })
        break
      case 'mid':
        onFilterChange({ min_experience_years: 3, max_experience_years: 5 })
        break
      case 'senior':
        onFilterChange({ min_experience_years: 5, max_experience_years: 8 })
        break
      case 'lead':
        onFilterChange({ min_experience_years: 8, max_experience_years: '' })
        break
      case 'all':
      default:
        onFilterChange({ min_experience_years: '', max_experience_years: '' })
        break
    }
  }

  const currentExpPreset = (() => {
    const min = filters.min_experience_years
    const max = filters.max_experience_years
    if (min === 0 && max === 2) return 'entry'
    if (min === 3 && max === 5) return 'mid'
    if (min === 5 && max === 8) return 'senior'
    if (min === 8 && (max === '' || max === undefined)) return 'lead'
    if ((min === '' || min === undefined) && (max === '' || max === undefined))
      return 'all'
    return 'custom'
  })()

  const hasActiveFilters = Boolean(
    filters.opportunity_type ||
      filters.work_mode ||
      filters.employment_type ||
      filters.location ||
      filters.min_experience_years !== undefined && filters.min_experience_years !== '' ||
      filters.max_experience_years !== undefined && filters.max_experience_years !== '' ||
      filters.keyword
  )

  return (
    <div className="space-y-4 rounded-xl border border-border bg-card/60 p-4 sm:p-5">
      {/* Top Bar: Search Keyword + Sort Select */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search by title, company, skills, or description..."
            value={filters.keyword || ''}
            onChange={(e) => onFilterChange({ keyword: e.target.value, page: 1 })}
            className="pl-9 bg-background"
          />
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="sort-select" className="text-xs font-medium text-muted-foreground whitespace-nowrap">
            Sort by:
          </label>
          <select
            id="sort-select"
            value={filters.sort_by || 'newest'}
            onChange={(e) =>
              onFilterChange({
                sort_by: e.target.value as OpportunitySortBy,
                page: 1,
              })
            }
            className="h-9 rounded-md border border-input bg-background px-3 py-1 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="deadline_soonest">Deadline Soonest</option>
            <option value="title_asc">Title (A-Z)</option>
          </select>
        </div>
      </div>

      {/* Opportunity Type Pill Buttons */}
      <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border/50">
        <span className="text-xs font-semibold text-muted-foreground mr-1">Type:</span>
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

      {/* Detailed Multi-Facet Row: Work Mode, Experience Preset, Location */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
        {/* Work Mode */}
        <div>
          <label htmlFor="work-mode-select" className="block text-xs font-medium text-muted-foreground mb-1">
            Work Mode
          </label>
          <select
            id="work-mode-select"
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
          </select>
        </div>

        {/* Experience Presets */}
        <div>
          <label htmlFor="experience-preset-select" className="block text-xs font-medium text-muted-foreground mb-1">
            Experience Level
          </label>
          <select
            id="experience-preset-select"
            value={currentExpPreset}
            onChange={(e) => {
              handleExperiencePreset(e.target.value)
              onFilterChange({ page: 1 })
            }}
            className="w-full h-8 rounded-md border border-input bg-background px-2.5 py-1 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="all">Any Experience</option>
            <option value="entry">Entry Level (0–2 yrs)</option>
            <option value="mid">Mid Level (3–5 yrs)</option>
            <option value="senior">Senior Level (5–8 yrs)</option>
            <option value="lead">Lead / Staff (8+ yrs)</option>
            {currentExpPreset === 'custom' && (
              <option value="custom">Custom Range</option>
            )}
          </select>
        </div>

        {/* Location Filter */}
        <div>
          <label htmlFor="location-input" className="block text-xs font-medium text-muted-foreground mb-1">
            Location
          </label>
          <Input
            id="location-input"
            type="text"
            placeholder="e.g. San Francisco, Remote, London"
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
            Filters applied ({totalCount} matching {totalCount === 1 ? 'opportunity' : 'opportunities'})
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
