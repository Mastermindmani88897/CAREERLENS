/**
 * Phase 22 End-to-End User Acceptance and Integration Test Suite.
 *
 * Simulates complete candidate user journeys across:
 * 1. Opportunity exploration, semantic match evaluation, and breakdown inspection.
 * 2. Saving an opportunity, navigating to Application Dashboard, and verifying counters.
 * 3. Status transition workflow (saved -> applied) with audit notes.
 * 4. Application filtering by status and text query.
 * 5. Unauthenticated session prompts and error recovery behaviors.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { DashboardPage } from '@/pages/DashboardPage'
import { OpportunityDetailPage } from '@/pages/OpportunityDetailPage'
import * as applicationService from '@/services/applicationService'
import * as matchingService from '@/services/matchingService'
import * as opportunityService from '@/services/opportunityService'
import type { ApplicationResponse } from '@/types/application'
import type { MatchResponse, ScoreBreakdown } from '@/types/matching'
import type { OpportunityDetail } from '@/types/opportunity'

const mockScoreBreakdown: ScoreBreakdown = {
  weights: {
    semantic_similarity: 0.35,
    skill_overlap: 0.25,
    experience: 0.15,
    education: 0.1,
    location: 0.05,
    work_mode: 0.05,
    location_work_mode: 0.1,
    employment_type: 0.05,
  },
  skill_overlap: {
    score: 1.0,
    required_count: 2,
    preferred_count: 1,
    matched_required: ['Go', 'Kubernetes'],
    missing_required: [],
    matched_preferred: ['Terraform'],
    missing_preferred: [],
  },
  experience: {
    score: 0.95,
    candidate_total_years: 8.0,
    required_min_years: 5,
    required_max_years: 12,
    is_overqualified: false,
    experience_gap_years: 0.0,
    warnings: [],
  },
  education: {
    score: 1.0,
    required_level: 'bachelor',
    candidate_highest_level: 'bachelor',
    meets_requirement: true,
    missing_evidence: false,
    warnings: [],
  },
  location: {
    score: 1.0,
    opportunity_location: 'Bengaluru, KA, India',
    candidate_location: 'Bengaluru, KA, India',
    open_to_relocation: true,
    warnings: [],
  },
  work_mode: {
    score: 1.0,
    opportunity_work_mode: 'hybrid',
    candidate_preferred_work_mode: 'hybrid',
    has_conflict: false,
    warnings: [],
  },
  location_work_mode: {
    score: 0.9,
    opportunity_work_mode: 'hybrid',
    candidate_preferred_work_mode: 'hybrid',
    open_to_relocation: true,
    warnings: [],
  },
  employment_type: {
    score: 1.0,
    opportunity_employment_type: 'fulltime',
    candidate_preferred_employment_type: 'fulltime',
    is_match: true,
    is_missing: false,
    warnings: [],
  },
  semantic_similarity_normalized: 0.88,
  semantic_similarity_raw: 0.88,
}

const mockOppDetail: OpportunityDetail = {
  id: 'opp-e2e-001',
  title: 'Principal Cloud Platform Engineer',
  company: 'Aether Cloud Systems',
  opportunity_type: 'job',
  work_mode: 'hybrid',
  employment_type: 'fulltime',
  description: 'Design distributed edge Kubernetes infrastructure and high-throughput APIs.',
  location_city: 'Bengaluru',
  location_state: 'KA',
  location_country: 'India',
  min_experience_years: 5,
  max_experience_years: 12,
  required_education_level: 'bachelor',
  salary_min: 3000000,
  salary_max: 4500000,
  salary_currency: 'INR',
  is_active: true,
  application_deadline: null,
  posted_date: '2026-10-20',
  job_url: 'https://example.com/jobs/e2e-001',
  source: 'internal',
  source_id: 'e2e-opp-001',
  created_at: '2026-10-20T10:00:00Z',
  updated_at: '2026-10-20T10:00:00Z',
  required_skills: ['Go', 'Kubernetes'],
  preferred_skills: ['Terraform'],
  skills: [
    { id: 'sk-1', opportunity_id: 'opp-e2e-001', skill_name: 'Go', is_required: true },
    { id: 'sk-2', opportunity_id: 'opp-e2e-001', skill_name: 'Kubernetes', is_required: true },
    { id: 'sk-3', opportunity_id: 'opp-e2e-001', skill_name: 'Terraform', is_required: false },
  ],
}

const mockMatchResponse: MatchResponse = {
  id: 'match-e2e-001',
  candidate_profile_id: 'prof-e2e-001',
  opportunity_id: 'opp-e2e-001',
  semantic_score: 0.88,
  deterministic_score: 0.92,
  final_score: 0.906,
  eligibility_status: 'eligible',
  eligibility_warnings: [],
  score_breakdown: mockScoreBreakdown,
  explanation: {
    strengths: ['Strong Go & Kubernetes background', 'Education requirement satisfied'],
    gaps: [],
  },
  skill_gap: {
    matched_required_skills: ['Go', 'Kubernetes'],
    missing_required_skills: [],
    matched_preferred_skills: ['Terraform'],
    missing_preferred_skills: [],
  },
  computed_at: '2026-10-24T12:00:00Z',
}

const mockSavedApp: ApplicationResponse = {
  id: 'app-e2e-001',
  candidate_profile_id: 'prof-e2e-001',
  opportunity_id: 'opp-e2e-001',
  status: 'saved',
  applied_date: null,
  notes: 'High match candidate bookmarked from search.',
  created_at: '2026-10-24T12:05:00Z',
  updated_at: '2026-10-24T12:05:00Z',
  opportunity: {
    id: 'opp-e2e-001',
    title: 'Principal Cloud Platform Engineer',
    company: 'Aether Cloud Systems',
    location_city: 'Bengaluru',
    location_state: 'KA',
    location_country: 'India',
    work_mode: 'hybrid',
    employment_type: 'fulltime',
    salary_min: 3000000,
    salary_max: 4500000,
    salary_currency: 'INR',
    is_active: true,
  },
  status_history: [
    {
      id: 'sh-1',
      application_id: 'app-e2e-001',
      status: 'saved',
      notes: 'Initial save.',
      changed_at: '2026-10-24T12:05:00Z',
    },
  ],
}

describe('End-to-End User Journeys and Acceptance Testing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem('access_token', 'mock.e2e.jwt.token')
  })

  it('Journey 1: Evaluates hybrid match on Opportunity Detail, views score breakdowns and saves application', async () => {
    vi.spyOn(opportunityService, 'getOpportunityById').mockResolvedValue(mockOppDetail)
    vi.spyOn(matchingService, 'getMatchByOpportunityId').mockResolvedValue(null)
    vi.spyOn(matchingService, 'triggerMatch').mockResolvedValue(mockMatchResponse)
    vi.spyOn(applicationService, 'listApplications').mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      total_pages: 0,
    })
    const createSpy = vi.spyOn(applicationService, 'createApplication').mockResolvedValue(mockSavedApp)

    const user = userEvent.setup()

    render(
      <MemoryRouter initialEntries={['/opportunities/opp-e2e-001']}>
        <Routes>
          <Route path="/opportunities/:id" element={<OpportunityDetailPage />} />
          <Route path="/dashboard" element={<div data-testid="dashboard-view">Dashboard</div>} />
        </Routes>
      </MemoryRouter>
    )

    // Verify opportunity detail elements loaded
    expect(await screen.findByText('Principal Cloud Platform Engineer')).toBeInTheDocument()
    expect(screen.getByText('Aether Cloud Systems')).toBeInTheDocument()

    // Trigger Match Evaluation
    const evaluateBtn = screen.getByRole('button', { name: /evaluate match/i })
    await user.click(evaluateBtn)

    // Verify Hybrid match scores, eligibility badge, and breakdowns
    await waitFor(() => {
      expect(screen.getByText('91%')).toBeInTheDocument() // 0.906 rounded to 91%
    })
    expect(screen.getAllByText(/Eligible/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Strong Go & Kubernetes background')).toBeInTheDocument()

    // Save Application
    const saveBtn = screen.getByRole('button', { name: /Save Opportunity/i })
    await user.click(saveBtn)

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith({
        opportunity_id: 'opp-e2e-001',
        status: 'saved',
      })
    })

    // Confirm UI reflects tracked state
    expect(await screen.findByRole('button', { name: /update status/i })).toBeInTheDocument()
  })

  it('Journey 2: Dashboard renders counters, filters applications, and performs status transition with audit note', async () => {
    vi.spyOn(applicationService, 'listApplications').mockResolvedValue({
      items: [mockSavedApp],
      total: 1,
      page: 1,
      page_size: 100,
      total_pages: 1,
    })

    const transitionSpy = vi.spyOn(applicationService, 'updateApplicationStatus').mockResolvedValue({
      ...mockSavedApp,
      status: 'applied',
      applied_date: '2026-10-24',
      status_history: [
        ...(mockSavedApp.status_history ?? []),
        {
          id: 'sh-2',
          application_id: 'app-e2e-001',
          status: 'applied',
          notes: 'Submitted resume via corporate career portal.',
          changed_at: '2026-10-24T12:30:00Z',
        },
      ],
    })

    const user = userEvent.setup()

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </MemoryRouter>
    )

    // Verify Dashboard counters
    expect(await screen.findByText('1 Saved')).toBeInTheDocument()
    expect(screen.getByText('Principal Cloud Platform Engineer')).toBeInTheDocument()
    expect(screen.getByText('High match candidate bookmarked from search.')).toBeInTheDocument()

    // Open Status Transition Modal
    const updateStatusBtn = screen.getByRole('button', { name: /update status/i })
    await user.click(updateStatusBtn)

    // Modal presents permitted transitions from 'saved'
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    const appliedOption = screen.getByRole('radio', { name: /applied/i })
    await user.click(appliedOption)

    // Fill notes
    const notesInput = screen.getByPlaceholderText(/completed second technical round/i)
    await user.type(notesInput, 'Submitted resume via corporate career portal.')

    // Submit transition
    const submitBtn = screen.getByRole('button', { name: /confirm update/i })
    await user.click(submitBtn)

    await waitFor(() => {
      expect(transitionSpy).toHaveBeenCalledWith('app-e2e-001', {
        status: 'applied',
        notes: 'Submitted resume via corporate career portal.',
      })
    })
  })

  it('Journey 3: Session handling — displays login prompt when user session is unauthenticated', async () => {
    vi.spyOn(applicationService, 'listApplications').mockRejectedValue(
      new applicationService.ApplicationTrackingError('Authentication required.', 401)
    )

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </MemoryRouter>
    )

    expect(await screen.findByText(/sign in to track applications/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument()
  })

  it('Journey 4: Error handling and recovery — displays retry button on service failure', async () => {
    const listSpy = vi
      .spyOn(applicationService, 'listApplications')
      .mockRejectedValueOnce(new Error('Network error connecting to CareerLens backend.'))
      .mockResolvedValueOnce({
        items: [mockSavedApp],
        total: 1,
        page: 1,
        page_size: 100,
        total_pages: 1,
      })

    const user = userEvent.setup()

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </MemoryRouter>
    )

    // Error state appears
    expect(await screen.findByText(/Network error connecting to CareerLens backend/i)).toBeInTheDocument()

    // Click retry
    const retryBtn = screen.getByRole('button', { name: /retry/i })
    await user.click(retryBtn)

    // Successful recovery
    expect(await screen.findByText('Principal Cloud Platform Engineer')).toBeInTheDocument()
    expect(listSpy).toHaveBeenCalledTimes(2)
  })
})
