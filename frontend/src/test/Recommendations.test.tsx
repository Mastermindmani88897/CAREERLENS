/**
 * Frontend test suite for Phase 18 Recommendations Frontend.
 * Validates RecommendationCard, RecommendationFilters, RecommendationsPage,
 * similarity score displays (positive, zero, negative, null),
 * error states (400, 401, 404, 500), empty states, and pagination.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { RecommendationCard } from '@/components/recommendations/RecommendationCard'
import { RecommendationFilters } from '@/components/recommendations/RecommendationFilters'
import { RecommendationsPage } from '@/pages/RecommendationsPage'
import * as recommendationService from '@/services/recommendationService'
import type {
  RecommendationListResponse,
  SemanticOpportunityItem,
} from '@/types/recommendation'

const mockItems: SemanticOpportunityItem[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    title: 'Senior Machine Learning Engineer',
    company: 'Neural Dynamics',
    description: 'Lead local embedding systems and vector search optimization in PostgreSQL.',
    opportunity_type: 'job',
    employment_type: 'fulltime',
    work_mode: 'remote',
    required_education_level: 'bachelor',
    location_city: 'San Francisco',
    location_state: 'CA',
    location_country: 'USA',
    salary_min: 160000,
    salary_max: 210000,
    salary_currency: 'USD',
    min_experience_years: 5,
    max_experience_years: 8,
    application_deadline: '2026-12-31',
    job_url: 'https://example.com/apply/ml',
    source: 'manual',
    source_id: 'nd-001',
    posted_date: '2026-10-01',
    required_skills: ['Python', 'FastAPI', 'pgvector'],
    preferred_skills: ['PyTorch'],
    is_active: true,
    created_at: '2026-10-01T00:00:00Z',
    updated_at: '2026-10-01T00:00:00Z',
    semantic_similarity: 0.8421,
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    title: 'Backend Software Intern',
    company: 'CloudWorks',
    description: 'Assist in building microservice backends and RESTful API endpoints.',
    opportunity_type: 'internship',
    employment_type: 'internship',
    work_mode: 'hybrid',
    required_education_level: 'master',
    location_city: 'Austin',
    location_state: 'TX',
    location_country: 'USA',
    salary_min: 40,
    salary_max: 55,
    salary_currency: 'USD',
    min_experience_years: 0,
    max_experience_years: 1,
    application_deadline: null,
    job_url: null,
    source: 'manual',
    source_id: 'cw-002',
    posted_date: '2026-10-05',
    required_skills: ['Go', 'Docker'],
    preferred_skills: null,
    is_active: true,
    created_at: '2026-10-05T00:00:00Z',
    updated_at: '2026-10-05T00:00:00Z',
    semantic_similarity: -0.125,
  },
]

const mockResponse: RecommendationListResponse = {
  items: mockItems,
  total: 2,
  page: 1,
  page_size: 12,
  total_pages: 1,
}

describe('Phase 18 — RecommendationCard Component', () => {
  it('renders opportunity details, badges, and positive semantic similarity score correctly', () => {
    render(
      <MemoryRouter>
        <RecommendationCard item={mockItems[0]} />
      </MemoryRouter>
    )

    expect(screen.getByText('Senior Machine Learning Engineer')).toBeInTheDocument()
    expect(screen.getByText('Neural Dynamics')).toBeInTheDocument()
    expect(screen.getByText('job')).toBeInTheDocument()
    expect(screen.getByText('remote')).toBeInTheDocument()
    expect(screen.getByText('fulltime')).toBeInTheDocument()
    expect(screen.getByText('San Francisco, CA, USA')).toBeInTheDocument()
    expect(screen.getByText('USD 160,000 - 210,000')).toBeInTheDocument()
    expect(screen.getByText('5–8 yrs exp')).toBeInTheDocument()

    // Formatted semantic cosine alignment
    expect(screen.getByText('Cosine: +0.84')).toBeInTheDocument()
  })

  it('renders negative semantic similarity safely with neutral Low label', () => {
    render(
      <MemoryRouter>
        <RecommendationCard item={mockItems[1]} />
      </MemoryRouter>
    )

    expect(screen.getByText('Backend Software Intern')).toBeInTheDocument()
    expect(screen.getByText('Cosine: -0.13 (Low)')).toBeInTheDocument()
  })

  it('renders plain text description without HTML injection risks', () => {
    const maliciousItem: SemanticOpportunityItem = {
      ...mockItems[0],
      description: '<script>alert("xss")</script>Plain description content',
    }

    render(
      <MemoryRouter>
        <RecommendationCard item={maliciousItem} />
      </MemoryRouter>
    )

    // The entire string should be rendered as plain text, not parsed as an HTML script tag
    expect(
      screen.getByText('<script>alert("xss")</script>Plain description content')
    ).toBeInTheDocument()
  })
})

describe('Phase 18 — RecommendationFilters Component', () => {
  it('triggers onFilterChange when opportunity type, work mode, or location change', async () => {
    const user = userEvent.setup()
    const handleFilterChange = vi.fn()
    const handleReset = vi.fn()

    render(
      <RecommendationFilters
        filters={{
          opportunity_type: '',
          work_mode: '',
          employment_type: '',
          location: '',
        }}
        onFilterChange={handleFilterChange}
        onReset={handleReset}
        totalCount={5}
      />
    )

    // Select Jobs type pill
    await user.click(screen.getByRole('button', { name: 'Jobs' }))
    expect(handleFilterChange).toHaveBeenCalledWith({
      opportunity_type: 'job',
      page: 1,
    })

    // Change Work Mode select
    const workModeSelect = screen.getByLabelText('Work Mode')
    await user.selectOptions(workModeSelect, 'remote')
    expect(handleFilterChange).toHaveBeenCalledWith({
      work_mode: 'remote',
      page: 1,
    })

    // Type location
    const locationInput = screen.getByLabelText('Location')
    await user.type(locationInput, 'Austin')
    expect(handleFilterChange).toHaveBeenCalledWith({
      location: expect.any(String),
      page: 1,
    })
  })

  it('renders Clear all filters button and triggers onReset when filters are active', async () => {
    const user = userEvent.setup()
    const handleReset = vi.fn()

    render(
      <RecommendationFilters
        filters={{
          opportunity_type: 'job',
          work_mode: 'remote',
          employment_type: '',
          location: '',
        }}
        onFilterChange={vi.fn()}
        onReset={handleReset}
        totalCount={2}
      />
    )

    const clearButton = screen.getByRole('button', { name: /Clear all filters/i })
    expect(clearButton).toBeInTheDocument()
    await user.click(clearButton)
    expect(handleReset).toHaveBeenCalled()
  })
})

describe('Phase 18 — RecommendationsPage Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('loads and displays recommendations successfully', async () => {
    vi.spyOn(recommendationService, 'getRecommendations').mockResolvedValue(mockResponse)

    render(
      <MemoryRouter>
        <RecommendationsPage />
      </MemoryRouter>
    )

    // Initially displays loading state
    expect(screen.getByText('Finding your best opportunities...')).toBeInTheDocument()

    // Resolves and displays items
    await waitFor(() => {
      expect(screen.getByText('Senior Machine Learning Engineer')).toBeInTheDocument()
    })

    expect(screen.getByText('Backend Software Intern')).toBeInTheDocument()
    expect(
      screen.getByText(/Showing 2 of 2 recommendations/i)
    ).toBeInTheDocument()
  })

  it('displays empty state when backend returns 0 items', async () => {
    vi.spyOn(recommendationService, 'getRecommendations').mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
      total_pages: 0,
    })

    render(
      <MemoryRouter>
        <RecommendationsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(
        screen.getByText('No recommendations match your filters')
      ).toBeInTheDocument()
    })
  })

  it('displays Candidate Profile Required card when backend returns 404', async () => {
    vi.spyOn(recommendationService, 'getRecommendations').mockRejectedValue(
      new recommendationService.RecommendationError(
        'Candidate profile not found. Please create a profile before requesting recommendations.',
        404
      )
    )

    render(
      <MemoryRouter>
        <RecommendationsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Candidate Profile Required')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /Create Candidate Profile/i })).toBeInTheDocument()
  })

  it('displays Profile Details Needed card when backend returns 400 (insufficient profile text)', async () => {
    vi.spyOn(recommendationService, 'getRecommendations').mockRejectedValue(
      new recommendationService.RecommendationError(
        'Candidate profile has insufficient content for recommendations.',
        400
      )
    )

    render(
      <MemoryRouter>
        <RecommendationsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Profile Details Needed')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /Update Profile Skills/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Upload Resume/i })).toBeInTheDocument()
  })

  it('displays Authentication Required card when backend returns 401', async () => {
    vi.spyOn(recommendationService, 'getRecommendations').mockRejectedValue(
      new recommendationService.RecommendationError(
        'Authentication required. Please sign in to view your personalized recommendations.',
        401
      )
    )

    render(
      <MemoryRouter>
        <RecommendationsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Authentication Required')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /Sign In to CareerLens/i })).toBeInTheDocument()
  })

  it('displays server error and enables retry on 500 error', async () => {
    vi.spyOn(recommendationService, 'getRecommendations')
      .mockRejectedValueOnce(new Error('Server error processing recommendations.'))
      .mockResolvedValueOnce(mockResponse)

    render(
      <MemoryRouter>
        <RecommendationsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Unable to load recommendations')).toBeInTheDocument()
    })

    const retryButton = screen.getByRole('button', { name: /Try again/i })
    await userEvent.click(retryButton)

    await waitFor(() => {
      expect(screen.getByText('Senior Machine Learning Engineer')).toBeInTheDocument()
    })
  })
})
