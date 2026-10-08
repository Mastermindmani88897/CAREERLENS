/**
 * Frontend test suite for Phase 15 Opportunity Discovery.
 * Validates OpportunityCard, OpportunityFilters, OpportunitiesPage,
 * OpportunityDetailPage, and safe link attributes.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { OpportunityCard } from '@/components/opportunities/OpportunityCard'
import { OpportunityFilters } from '@/components/opportunities/OpportunityFilters'
import { OpportunitiesPage } from '@/pages/OpportunitiesPage'
import { OpportunityDetailPage } from '@/pages/OpportunityDetailPage'
import * as opportunityService from '@/services/opportunityService'
import type {
  Opportunity,
  OpportunityDetail,
  OpportunityListResponse,
} from '@/types/opportunity'

const mockOpportunities: Opportunity[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    title: 'Senior Frontend Engineer',
    company: 'TechCorp',
    description: 'Looking for a Senior React Engineer with deep TypeScript skills.',
    opportunity_type: 'job',
    employment_type: 'fulltime',
    work_mode: 'remote',
    required_education_level: 'bachelor',
    location_city: 'San Francisco',
    location_state: 'CA',
    location_country: 'USA',
    salary_min: 140000,
    salary_max: 180000,
    salary_currency: 'USD',
    min_experience_years: 5,
    max_experience_years: 8,
    application_deadline: '2026-12-31',
    job_url: 'https://techcorp.example.com/apply/frontend',
    source: 'manual',
    source_id: 'tc-001',
    posted_date: '2026-10-01',
    required_skills: ['React', 'TypeScript', 'TailwindCSS'],
    preferred_skills: ['Next.js'],
    is_active: true,
    created_at: '2026-10-01T00:00:00Z',
    updated_at: '2026-10-01T00:00:00Z',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    title: 'AI Systems Research Intern',
    company: 'DeepResearch Labs',
    description: 'Exciting summer internship working on LLM inference and reasoning.',
    opportunity_type: 'internship',
    employment_type: 'internship',
    work_mode: 'hybrid',
    required_education_level: 'master',
    location_city: 'Boston',
    location_state: 'MA',
    location_country: 'USA',
    salary_min: 50,
    salary_max: 65,
    salary_currency: 'USD',
    min_experience_years: 0,
    max_experience_years: 2,
    application_deadline: '2026-11-15',
    job_url: 'https://deepresearch.example.com/internships',
    source: 'manual',
    source_id: 'dr-002',
    posted_date: '2026-10-05',
    required_skills: ['Python', 'PyTorch'],
    preferred_skills: ['CUDA'],
    is_active: true,
    created_at: '2026-10-05T00:00:00Z',
    updated_at: '2026-10-05T00:00:00Z',
  },
]

const mockDetail: OpportunityDetail = {
  ...mockOpportunities[0],
  skills: [
    {
      id: 's-1',
      opportunity_id: mockOpportunities[0].id,
      skill_name: 'React',
      is_required: true,
    },
    {
      id: 's-2',
      opportunity_id: mockOpportunities[0].id,
      skill_name: 'TypeScript',
      is_required: true,
    },
    {
      id: 's-3',
      opportunity_id: mockOpportunities[0].id,
      skill_name: 'Next.js',
      is_required: false,
    },
  ],
}

describe('Phase 15 Opportunity Discovery Frontend', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders OpportunityCard with badges, compensation, and skill tags', () => {
    render(
      <MemoryRouter>
        <OpportunityCard opportunity={mockOpportunities[0]} />
      </MemoryRouter>
    )

    expect(screen.getByText('Senior Frontend Engineer')).toBeInTheDocument()
    expect(screen.getByText('TechCorp')).toBeInTheDocument()
    expect(screen.getByText('San Francisco, CA, USA')).toBeInTheDocument()
    expect(screen.getByText(/140,000/)).toBeInTheDocument()
    expect(screen.getByText('5–8 yrs exp')).toBeInTheDocument()
    expect(screen.getByText('React')).toBeInTheDocument()
    expect(screen.getByText('TypeScript')).toBeInTheDocument()
    expect(screen.getByText(/View Details/)).toBeInTheDocument()
  })

  it('renders OpportunityFilters with keyword input, type pills, and preset selections', async () => {
    const handleFilterChange = vi.fn()
    const handleReset = vi.fn()

    render(
      <OpportunityFilters
        filters={{ keyword: 'Python', opportunity_type: 'job' }}
        onFilterChange={handleFilterChange}
        onReset={handleReset}
        totalCount={5}
      />
    )

    const searchInput = screen.getByPlaceholderText(/Search by title, company, skills/i)
    expect(searchInput).toHaveValue('Python')

    const internshipsPill = screen.getByRole('button', { name: 'Internships' })
    await userEvent.click(internshipsPill)
    expect(handleFilterChange).toHaveBeenCalledWith({ opportunity_type: 'internship', page: 1 })

    const clearButton = screen.getByRole('button', { name: /Clear all filters/i })
    await userEvent.click(clearButton)
    expect(handleReset).toHaveBeenCalled()
  })

  it('renders OpportunitiesPage, fetches list, and displays opportunities', async () => {
    const listResponse: OpportunityListResponse = {
      items: mockOpportunities,
      total: 2,
      page: 1,
      page_size: 12,
      total_pages: 1,
    }

    vi.spyOn(opportunityService, 'getOpportunities').mockResolvedValue(listResponse)

    render(
      <MemoryRouter>
        <OpportunitiesPage />
      </MemoryRouter>
    )

    expect(screen.getByText(/Discovering opportunities/i)).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Senior Frontend Engineer')).toBeInTheDocument()
      expect(screen.getByText('AI Systems Research Intern')).toBeInTheDocument()
    })

    expect(screen.getByText(/Showing 2 of 2 results/i)).toBeInTheDocument()
  })

  it('renders empty state when no opportunities match criteria', async () => {
    const emptyResponse: OpportunityListResponse = {
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
      total_pages: 0,
    }

    vi.spyOn(opportunityService, 'getOpportunities').mockResolvedValue(emptyResponse)

    render(
      <MemoryRouter>
        <OpportunitiesPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/No matching opportunities found/i)).toBeInTheDocument()
    })
  })

  it('renders OpportunityDetailPage with plain text description and verified safe external link', async () => {
    vi.spyOn(opportunityService, 'getOpportunityById').mockResolvedValue(mockDetail)

    render(
      <MemoryRouter initialEntries={[`/opportunities/${mockDetail.id}`]}>
        <Routes>
          <Route path="/opportunities/:id" element={<OpportunityDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Senior Frontend Engineer')).toBeInTheDocument()
      expect(screen.getByText('TechCorp')).toBeInTheDocument()
      expect(screen.getByText(/Looking for a Senior React Engineer/i)).toBeInTheDocument()
    })

    // Verify skills
    expect(screen.getByText('React')).toBeInTheDocument()
    expect(screen.getByText('Next.js')).toBeInTheDocument()

    // Verify external link security
    const applyLink = screen.getByRole('link', { name: /Apply on Official Site/i })
    expect(applyLink).toHaveAttribute('href', 'https://techcorp.example.com/apply/frontend')
    expect(applyLink).toHaveAttribute('target', '_blank')
    expect(applyLink).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
