/**
 * Frontend test suite for Phase 20: Opportunity Exploration & Recommendation Frontend.
 * Tests matching components, eligibility statuses, seven-factor breakdown, skill gaps,
 * warnings, matching service client, and page integration.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { EligibilityBadge } from '@/components/matching/EligibilityBadge'
import { MatchExplanationCard } from '@/components/matching/MatchExplanationCard'
import { MatchScoreCard } from '@/components/matching/MatchScoreCard'
import { MatchWarningsList } from '@/components/matching/MatchWarningsList'
import { SevenFactorBreakdown } from '@/components/matching/SevenFactorBreakdown'
import { SkillGapCard } from '@/components/matching/SkillGapCard'
import { OpportunityDetailPage } from '@/pages/OpportunityDetailPage'
import { RecommendationsPage } from '@/pages/RecommendationsPage'
import * as matchingService from '@/services/matchingService'
import * as opportunityService from '@/services/opportunityService'
import * as recommendationService from '@/services/recommendationService'
import type {
  MatchListResponse,
  MatchResponse,
  ScoreBreakdown,
  SkillGap,
} from '@/types/matching'
import type { OpportunityDetail } from '@/types/opportunity'
import type { RecommendationListResponse } from '@/types/recommendation'

const mockScoreBreakdown: ScoreBreakdown = {
  weights: {
    semantic_similarity: 0.35,
    skill_overlap: 0.25,
    experience: 0.15,
    education: 0.10,
    location: 0.05,
    work_mode: 0.05,
    location_work_mode: 0.10,
    employment_type: 0.05,
  },
  skill_overlap: {
    score: 0.85,
    required_count: 3,
    preferred_count: 1,
    matched_required: ['React', 'TypeScript'],
    missing_required: ['GraphQL'],
    matched_preferred: ['TailwindCSS'],
    missing_preferred: [],
  },
  experience: {
    score: 1.0,
    candidate_total_years: 5.5,
    required_min_years: 4,
    required_max_years: 7,
    is_overqualified: false,
    experience_gap_years: 0.0,
    warnings: [],
  },
  education: {
    score: 1.0,
    required_level: 'bachelor',
    candidate_highest_level: 'master',
    meets_requirement: true,
    missing_evidence: false,
    warnings: [],
  },
  location: {
    score: 1.0,
    opportunity_location: 'San Francisco, CA',
    candidate_location: 'San Francisco, CA',
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
    score: 1.0,
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
  semantic_similarity_raw: 0.8812,
}

const mockSkillGap: SkillGap = {
  matched_required_skills: ['React', 'TypeScript'],
  missing_required_skills: ['GraphQL'],
  matched_preferred_skills: ['TailwindCSS'],
  missing_preferred_skills: ['Docker'],
}

const mockMatchResponse: MatchResponse = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  candidate_profile_id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  opportunity_id: '11111111-1111-1111-1111-111111111111',
  semantic_score: 0.88,
  deterministic_score: 0.95,
  final_score: 0.84,
  eligibility_status: 'eligible',
  eligibility_warnings: ['Candidate should review work schedule flexibility.'],
  score_breakdown: mockScoreBreakdown,
  explanation: {
    strengths: [
      'Exceeds education requirements with a master degree.',
      'Strong skill overlap on core technical stack.',
    ],
    gaps: ['Missing required skill: GraphQL.'],
  },
  skill_gap: mockSkillGap,
  computed_at: '2026-10-24T10:00:00Z',
}

const mockOppDetail: OpportunityDetail = {
  id: '11111111-1111-1111-1111-111111111111',
  title: 'Staff Frontend Engineer',
  company: 'InnovateTech',
  description: 'Looking for a Staff Engineer to architect scalable React web applications.',
  opportunity_type: 'job',
  employment_type: 'fulltime',
  work_mode: 'hybrid',
  required_education_level: 'bachelor',
  location_city: 'San Francisco',
  location_state: 'CA',
  location_country: 'USA',
  salary_min: 180000,
  salary_max: 220000,
  salary_currency: 'USD',
  min_experience_years: 5,
  max_experience_years: 8,
  application_deadline: '2026-12-31',
  job_url: 'https://example.com/jobs/staff-frontend',
  source: 'manual',
  source_id: 'it-001',
  posted_date: '2026-10-10',
  required_skills: ['React', 'TypeScript', 'GraphQL'],
  preferred_skills: ['TailwindCSS'],
  is_active: true,
  created_at: '2026-10-10T00:00:00Z',
  updated_at: '2026-10-10T00:00:00Z',
  skills: [
    {
      id: 's-1',
      opportunity_id: '11111111-1111-1111-1111-111111111111',
      skill_name: 'React',
      is_required: true,
    },
    {
      id: 's-2',
      opportunity_id: '11111111-1111-1111-1111-111111111111',
      skill_name: 'TypeScript',
      is_required: true,
    },
    {
      id: 's-3',
      opportunity_id: '11111111-1111-1111-1111-111111111111',
      skill_name: 'GraphQL',
      is_required: true,
    },
  ],
}

describe('Phase 20 — EligibilityBadge Component', () => {
  it('renders ELIGIBLE status with accessible status role and label', () => {
    render(<EligibilityBadge status="eligible" />)
    const badge = screen.getByRole('status')
    expect(badge).toHaveTextContent('ELIGIBLE')
    expect(badge).toHaveAttribute('aria-label', expect.stringContaining('Eligible'))
  })

  it('renders PARTIAL status with accessible status role and label', () => {
    render(<EligibilityBadge status="partial" />)
    const badge = screen.getByRole('status')
    expect(badge).toHaveTextContent('PARTIAL')
    expect(badge).toHaveAttribute('aria-label', expect.stringContaining('Partial'))
  })

  it('renders REVIEW REQUIRED status with accessible status role and label', () => {
    render(<EligibilityBadge status="review_required" />)
    const badge = screen.getByRole('status')
    expect(badge).toHaveTextContent('REVIEW REQUIRED')
    expect(badge).toHaveAttribute('aria-label', expect.stringContaining('Review Required'))
  })
})

describe('Phase 20 — MatchScoreCard Component', () => {
  it('renders final score percentage, subscores, and mandatory ranking-aid disclaimer', () => {
    render(
      <MatchScoreCard
        finalScore={0.84}
        semanticScore={0.88}
        deterministicScore={0.95}
        eligibilityStatus="eligible"
        computedAt="2026-10-24T10:00:00Z"
      />
    )

    expect(screen.getByText('84%')).toBeInTheDocument()
    expect(screen.getByText('88%')).toBeInTheDocument()
    expect(screen.getByText('95%')).toBeInTheDocument()
    expect(screen.getByText('ELIGIBLE')).toBeInTheDocument()

    // Mandatory ranking-aid disclaimer
    expect(
      screen.getByText(/A match score is a ranking aid to help prioritize opportunities/i)
    ).toBeInTheDocument()
  })
})

describe('Phase 20 — SevenFactorBreakdown Component', () => {
  it('renders all seven scoring factors with approved weights and score percentages', () => {
    render(<SevenFactorBreakdown breakdown={mockScoreBreakdown} />)

    expect(screen.getByText('Seven-Factor Score Breakdown')).toBeInTheDocument()

    // 1. Semantic Similarity (35%)
    expect(screen.getByText('Semantic Similarity')).toBeInTheDocument()
    expect(screen.getByText('(35% weight)')).toBeInTheDocument()

    // 2. Skill Overlap (25%)
    expect(screen.getByText('Required & Preferred Skills')).toBeInTheDocument()
    expect(screen.getByText('(25% weight)')).toBeInTheDocument()

    // 3. Experience (15%)
    expect(screen.getByText('Experience Duration')).toBeInTheDocument()
    expect(screen.getByText('(15% weight)')).toBeInTheDocument()

    // 4. Education (10%)
    expect(screen.getByText('Education Attainment')).toBeInTheDocument()
    expect(screen.getByText('(10% weight)')).toBeInTheDocument()

    // 5, 6, 7. Location, Work Mode, Employment Type (5% weight each)
    expect(screen.getByText('Geographic Location')).toBeInTheDocument()
    expect(screen.getByText('Work Mode Alignment')).toBeInTheDocument()
    expect(screen.getByText('Employment Type')).toBeInTheDocument()
    expect(screen.getAllByText('(5% weight)')).toHaveLength(3)
  })
})

describe('Phase 20 — SkillGapCard Component', () => {
  it('renders matched required, missing required, and preferred skills', () => {
    render(<SkillGapCard skillGap={mockSkillGap} />)

    expect(screen.getByText(/Matched Required Skills \(2\)/i)).toBeInTheDocument()
    expect(screen.getByText('React')).toBeInTheDocument()
    expect(screen.getByText('TypeScript')).toBeInTheDocument()

    expect(screen.getByText(/Missing Required Skills \(1\)/i)).toBeInTheDocument()
    expect(screen.getByText('GraphQL')).toBeInTheDocument()

    expect(screen.getByText(/Matched Preferred Skills \(1\)/i)).toBeInTheDocument()
    expect(screen.getByText('TailwindCSS')).toBeInTheDocument()

    expect(screen.getByText(/Missing Preferred Skills \(1\)/i)).toBeInTheDocument()
    expect(screen.getByText('Docker')).toBeInTheDocument()
  })
})

describe('Phase 20 — MatchWarningsList & Explanation Components', () => {
  it('renders structured warnings banner when warnings exist', () => {
    render(
      <MatchWarningsList
        warnings={['Severe experience shortfall: 1.0 years vs 5.0 required', 'Work mode conflict']}
      />
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/Eligibility Warnings & Gaps \(2\)/i)).toBeInTheDocument()
    expect(
      screen.getByText('Severe experience shortfall: 1.0 years vs 5.0 required')
    ).toBeInTheDocument()
    expect(screen.getByText('Work mode conflict')).toBeInTheDocument()
  })

  it('renders nothing when warnings array is empty', () => {
    const { container } = render(<MatchWarningsList warnings={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders strengths and gaps from MatchExplanationCard', () => {
    render(
      <MatchExplanationCard
        explanation={{
          strengths: ['Great education match'],
          gaps: ['Missing skill: Python'],
        }}
      />
    )

    expect(screen.getByText('Key Strengths (1)')).toBeInTheDocument()
    expect(screen.getByText('Great education match')).toBeInTheDocument()
    expect(screen.getByText('Qualification Gaps (1)')).toBeInTheDocument()
    expect(screen.getByText('Missing skill: Python')).toBeInTheDocument()
  })
})

describe('Phase 20 — Matching API Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('getMatchByOpportunityId returns null on HTTP 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        status: 404,
        ok: false,
        json: async () => ({ detail: 'No match evaluation found' }),
      })
    )

    const result = await matchingService.getMatchByOpportunityId('opp-123')
    expect(result).toBeNull()
  })

  it('getMatchByOpportunityId returns match data on HTTP 200', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        json: async () => mockMatchResponse,
      })
    )

    const result = await matchingService.getMatchByOpportunityId('opp-123')
    expect(result).toEqual(mockMatchResponse)
    expect(fetch).toHaveBeenCalledWith('/api/v1/matches/opp-123', expect.any(Object))
  })

  it('triggerMatch calls POST /api/v1/matches/ with opportunity_id', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        json: async () => mockMatchResponse,
      })
    )

    const result = await matchingService.triggerMatch('opp-123', 0.85)
    expect(result).toEqual(mockMatchResponse)
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/matches/',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ opportunity_id: 'opp-123', semantic_similarity: 0.85 }),
      })
    )
  })

  it('evaluateMatches calls POST /api/v1/matches/evaluate', async () => {
    const listRes: MatchListResponse = {
      items: [
        {
          id: mockMatchResponse.id,
          candidate_profile_id: mockMatchResponse.candidate_profile_id,
          opportunity_id: mockMatchResponse.opportunity_id,
          semantic_score: 0.88,
          deterministic_score: 0.95,
          final_score: 0.84,
          eligibility_status: 'eligible',
          eligibility_warnings: null,
          computed_at: mockMatchResponse.computed_at,
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    }

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        json: async () => listRes,
      })
    )

    const result = await matchingService.evaluateMatches({ opportunity_ids: ['opp-123'] })
    expect(result).toEqual(listRes)
    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/matches/evaluate',
      expect.objectContaining({
        method: 'POST',
      })
    )
  })
})

describe('Phase 20 — OpportunityDetailPage Match Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('shows sign-in prompt when user is not authenticated', async () => {
    vi.spyOn(opportunityService, 'getOpportunityById').mockResolvedValue(mockOppDetail)

    render(
      <MemoryRouter initialEntries={[`/opportunities/${mockOppDetail.id}`]}>
        <Routes>
          <Route path="/opportunities/:id" element={<OpportunityDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Staff Frontend Engineer')).toBeInTheDocument()
    })

    expect(
      screen.getByText('Personalized Match & Eligibility Evaluation')
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Sign In to Evaluate Match/i })
    ).toBeInTheDocument()
  })

  it('shows Evaluate Match button when authenticated and match is not yet computed', async () => {
    localStorage.setItem('access_token', 'mock-valid-token')
    vi.spyOn(opportunityService, 'getOpportunityById').mockResolvedValue(mockOppDetail)
    vi.spyOn(matchingService, 'getMatchByOpportunityId').mockResolvedValue(null)
    const triggerSpy = vi.spyOn(matchingService, 'triggerMatch').mockResolvedValue(mockMatchResponse)

    render(
      <MemoryRouter initialEntries={[`/opportunities/${mockOppDetail.id}`]}>
        <Routes>
          <Route path="/opportunities/:id" element={<OpportunityDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Staff Frontend Engineer')).toBeInTheDocument()
      expect(screen.getByText('Evaluate Your Fit for This Role')).toBeInTheDocument()
    })

    const evaluateButton = screen.getByRole('button', { name: /^Evaluate Match$/i })
    expect(evaluateButton).toBeInTheDocument()

    // Trigger evaluation on explicit click
    await userEvent.click(evaluateButton)

    await waitFor(() => {
      expect(triggerSpy).toHaveBeenCalledWith(mockOppDetail.id)
      expect(screen.getByText('Match Evaluation & Eligibility Analysis')).toBeInTheDocument()
      expect(screen.getAllByText('ELIGIBLE').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('renders pre-computed match details immediately when authenticated', async () => {
    localStorage.setItem('access_token', 'mock-valid-token')
    vi.spyOn(opportunityService, 'getOpportunityById').mockResolvedValue(mockOppDetail)
    vi.spyOn(matchingService, 'getMatchByOpportunityId').mockResolvedValue(mockMatchResponse)

    render(
      <MemoryRouter initialEntries={[`/opportunities/${mockOppDetail.id}`]}>
        <Routes>
          <Route path="/opportunities/:id" element={<OpportunityDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Staff Frontend Engineer')).toBeInTheDocument()
      expect(screen.getByText('84%')).toBeInTheDocument()
      expect(screen.getByText('Seven-Factor Score Breakdown')).toBeInTheDocument()
      expect(screen.getByText('Skill Gap Analysis')).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: /Re-evaluate Match/i })).toBeInTheDocument()
  })
})

describe('Phase 20 — RecommendationsPage Evaluated Matches Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('renders ranking aid disclaimer and allows switching to evaluated matches tab', async () => {
    const mockRecs: RecommendationListResponse = {
      items: [
        {
          id: mockOppDetail.id,
          title: mockOppDetail.title,
          company: mockOppDetail.company,
          description: mockOppDetail.description,
          opportunity_type: mockOppDetail.opportunity_type,
          employment_type: mockOppDetail.employment_type,
          work_mode: mockOppDetail.work_mode,
          required_education_level: mockOppDetail.required_education_level,
          location_city: mockOppDetail.location_city,
          location_state: mockOppDetail.location_state,
          location_country: mockOppDetail.location_country,
          salary_min: mockOppDetail.salary_min,
          salary_max: mockOppDetail.salary_max,
          salary_currency: mockOppDetail.salary_currency,
          min_experience_years: mockOppDetail.min_experience_years,
          max_experience_years: mockOppDetail.max_experience_years,
          application_deadline: mockOppDetail.application_deadline,
          job_url: mockOppDetail.job_url,
          source: mockOppDetail.source,
          source_id: mockOppDetail.source_id,
          posted_date: mockOppDetail.posted_date,
          required_skills: mockOppDetail.required_skills,
          preferred_skills: mockOppDetail.preferred_skills,
          is_active: mockOppDetail.is_active,
          created_at: mockOppDetail.created_at,
          updated_at: mockOppDetail.updated_at,
          semantic_similarity: 0.88,
        },
      ],
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    }

    vi.spyOn(recommendationService, 'getRecommendations').mockResolvedValue(mockRecs)
    const listMatchesSpy = vi.spyOn(matchingService, 'listMatches').mockResolvedValue({
      items: [
        {
          id: mockMatchResponse.id,
          candidate_profile_id: mockMatchResponse.candidate_profile_id,
          opportunity_id: mockOppDetail.id,
          semantic_score: 0.88,
          deterministic_score: 0.95,
          final_score: 0.84,
          eligibility_status: 'eligible',
          eligibility_warnings: null,
          computed_at: mockMatchResponse.computed_at,
        },
      ],
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    })

    localStorage.setItem('access_token', 'valid-token')

    render(
      <MemoryRouter>
        <RecommendationsPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Staff Frontend Engineer')).toBeInTheDocument()
    })

    // Ranking aid disclaimer is present
    expect(
      screen.getByText(/Match scores and semantic recommendations are ranking aids/i)
    ).toBeInTheDocument()

    // Switch to Evaluated Matches tab
    const matchesTabButton = screen.getByRole('button', { name: /Evaluated Matches/i })
    await userEvent.click(matchesTabButton)

    await waitFor(() => {
      expect(listMatchesSpy).toHaveBeenCalled()
      expect(screen.getByText('Eligibility Status:')).toBeInTheDocument()
      expect(screen.getByText('Min Score:')).toBeInTheDocument()
    })
  })
})
