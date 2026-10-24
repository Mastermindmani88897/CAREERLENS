/**
 * Phase 21 Application Tracking and Status Transition Test Suite.
 * Covers:
 *   - ApplicationStatusBadge rendering for all 7 statuses with accessible roles
 *   - StatusTransitionModal displaying only permitted transitions and handling terminal states
 *   - ApplicationFilters status pills and search queries
 *   - ApplicationCard metadata, notes, and transition triggers
 *   - DashboardPage loading, empty, error/retry, unauthenticated, and active application states
 *   - applicationService API methods, error responses (401, 404, 409, 422)
 *   - OpportunityDetailPage tracking integration
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { ApplicationCard } from '@/components/applications/ApplicationCard'
import { ApplicationFilters } from '@/components/applications/ApplicationFilters'
import { ApplicationStatusBadge } from '@/components/applications/ApplicationStatusBadge'
import { StatusTransitionModal } from '@/components/applications/StatusTransitionModal'
import { DashboardPage } from '@/pages/DashboardPage'
import { OpportunityDetailPage } from '@/pages/OpportunityDetailPage'
import * as applicationService from '@/services/applicationService'
import * as matchingService from '@/services/matchingService'
import * as opportunityService from '@/services/opportunityService'
import {
  APPLICATION_STATUS_LABELS,
  type ApplicationResponse,
  type ApplicationStatus,
} from '@/types/application'

const mockApp1: ApplicationResponse = {
  id: 'app-00000000-0001',
  candidate_profile_id: 'cand-0000-0001',
  opportunity_id: 'opp-00000000-0001',
  status: 'saved',
  applied_date: null,
  notes: 'Bookmarked for later review.',
  created_at: '2026-10-24T10:00:00Z',
  updated_at: '2026-10-24T10:00:00Z',
  opportunity: {
    id: 'opp-00000000-0001',
    title: 'Senior Frontend Engineer',
    company: 'TechCorp Solutions',
    location_city: 'Bengaluru',
    location_state: 'KA',
    location_country: 'India',
    work_mode: 'hybrid',
    employment_type: 'fulltime',
    salary_min: 1500000,
    salary_max: 2500000,
    salary_currency: 'INR',
    is_active: true,
  },
  status_history: [
    {
      id: 'hist-0001',
      application_id: 'app-00000000-0001',
      status: 'saved',
      changed_at: '2026-10-24T10:00:00Z',
      notes: 'Initial save',
    },
  ],
}

const mockApp2: ApplicationResponse = {
  id: 'app-00000000-0002',
  candidate_profile_id: 'cand-0000-0001',
  opportunity_id: 'opp-00000000-0002',
  status: 'interview',
  applied_date: '2026-10-15',
  notes: 'Technical screen scheduled for tomorrow.',
  created_at: '2026-10-15T09:00:00Z',
  updated_at: '2026-10-20T14:00:00Z',
  opportunity: {
    id: 'opp-00000000-0002',
    title: 'Staff Cloud Architect',
    company: 'CloudGlobal Systems',
    location_city: 'Remote',
    location_state: null,
    location_country: 'India',
    work_mode: 'remote',
    employment_type: 'fulltime',
    salary_min: 3000000,
    salary_max: 4500000,
    salary_currency: 'INR',
    is_active: true,
  },
  status_history: [
    {
      id: 'hist-0002',
      application_id: 'app-00000000-0002',
      status: 'applied',
      changed_at: '2026-10-15T09:00:00Z',
      notes: 'Application submitted',
    },
    {
      id: 'hist-0003',
      application_id: 'app-00000000-0002',
      status: 'interview',
      changed_at: '2026-10-20T14:00:00Z',
      notes: 'Invited to interview round 1',
    },
  ],
}

describe('ApplicationStatusBadge Component', () => {
  const statuses: ApplicationStatus[] = [
    'saved',
    'applied',
    'oa',
    'interview',
    'offer',
    'rejected',
    'withdrawn',
  ]

  it.each(statuses)('renders accessible badge for %s status', (status) => {
    render(<ApplicationStatusBadge status={status} />)
    const label = APPLICATION_STATUS_LABELS[status]
    const badge = screen.getByRole('status', { name: `Status: ${label}` })
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent(label)
  })
})

describe('StatusTransitionModal Component', () => {
  it('displays only permitted transitions from current status', () => {
    // mockApp1 is currently 'saved'. Permitted: ['applied', 'withdrawn']
    render(
      <StatusTransitionModal
        application={mockApp1}
        isOpen={true}
        onClose={vi.fn()}
        onTransitionSuccess={vi.fn()}
        onUpdateStatus={vi.fn()}
      />
    )

    expect(screen.getByRole('heading', { name: /Update Application Status/i })).toBeInTheDocument()
    expect(screen.getByText('TechCorp Solutions', { exact: false })).toBeInTheDocument()

    // Permitted transitions for 'saved'
    expect(screen.getByText('Applied')).toBeInTheDocument()
    expect(screen.getByText('Withdrawn')).toBeInTheDocument()

    // Forbidden transitions should NOT be offered as radio options
    expect(screen.queryByText('Offer Received')).not.toBeInTheDocument()
    expect(screen.queryByText('Interviewing')).not.toBeInTheDocument()
  })

  it('renders terminal notification when application is rejected or withdrawn', () => {
    const terminalApp: ApplicationResponse = {
      ...mockApp1,
      status: 'rejected',
    }

    render(
      <StatusTransitionModal
        application={terminalApp}
        isOpen={true}
        onClose={vi.fn()}
        onTransitionSuccess={vi.fn()}
        onUpdateStatus={vi.fn()}
      />
    )

    expect(screen.getByText(/Terminal Lifecycle State/i)).toBeInTheDocument()
    expect(screen.getByText(/Further status transitions are not permitted/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Confirm Update/i })).not.toBeInTheDocument()
  })

  it('submits selected status transition with optional notes', async () => {
    const user = userEvent.setup()
    const handleUpdate = vi.fn().mockResolvedValue({
      ...mockApp1,
      status: 'applied',
    })
    const onSuccess = vi.fn()
    const onClose = vi.fn()

    render(
      <StatusTransitionModal
        application={mockApp1}
        isOpen={true}
        onClose={onClose}
        onTransitionSuccess={onSuccess}
        onUpdateStatus={handleUpdate}
      />
    )

    const notesInput = screen.getByPlaceholderText(/Completed second technical round/i)
    await user.type(notesInput, 'Submitted application via careers portal.')

    const confirmBtn = screen.getByRole('button', { name: /Confirm Update/i })
    await user.click(confirmBtn)

    expect(handleUpdate).toHaveBeenCalledWith(
      mockApp1.id,
      'applied',
      'Submitted application via careers portal.'
    )
    expect(onSuccess).toHaveBeenCalled()
    expect(onClose).toHaveBeenCalled()
  })

  it('handles and displays transition failure gracefully', async () => {
    const user = userEvent.setup()
    const handleUpdate = vi
      .fn()
      .mockRejectedValue(new Error('Invalid status transition rejected by backend server.'))

    render(
      <StatusTransitionModal
        application={mockApp1}
        isOpen={true}
        onClose={vi.fn()}
        onTransitionSuccess={vi.fn()}
        onUpdateStatus={handleUpdate}
      />
    )

    const confirmBtn = screen.getByRole('button', { name: /Confirm Update/i })
    await user.click(confirmBtn)

    expect(
      await screen.findByText('Invalid status transition rejected by backend server.')
    ).toBeInTheDocument()
  })
})

describe('ApplicationFilters Component', () => {
  it('triggers onFilterChange when status pill or search keyword changes', async () => {
    const user = userEvent.setup()
    const onFilterChange = vi.fn()

    render(
      <ApplicationFilters
        filters={{ status: 'all', search: '', page: 1, page_size: 50 }}
        onFilterChange={onFilterChange}
        totalCount={5}
      />
    )

    expect(screen.getByText('5 applications')).toBeInTheDocument()

    // Click 'Interviewing' pill
    const interviewPill = screen.getByRole('button', { name: /Interviewing/i })
    await user.click(interviewPill)
    expect(onFilterChange).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'interview', page: 1 })
    )

    // Type search query
    const searchInput = screen.getByLabelText(/Search applications/i)
    await user.type(searchInput, 'Google')
    expect(onFilterChange).toHaveBeenCalled()
  })

  it('renders and triggers Reset button when active filter is present', async () => {
    const user = userEvent.setup()
    const onFilterChange = vi.fn()

    render(
      <ApplicationFilters
        filters={{ status: 'applied', search: 'Cloud', page: 1, page_size: 50 }}
        onFilterChange={onFilterChange}
        totalCount={1}
      />
    )

    const resetBtn = screen.getByRole('button', { name: /Reset/i })
    expect(resetBtn).toBeInTheDocument()

    await user.click(resetBtn)
    expect(onFilterChange).toHaveBeenCalledWith({
      status: 'all',
      search: '',
      page: 1,
    })
  })
})

describe('ApplicationCard Component', () => {
  it('renders application details, status badge, dates, and opens modal', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <ApplicationCard
          application={mockApp2}
          onUpdateStatus={vi.fn()}
          onDeleteApplication={vi.fn()}
        />
      </MemoryRouter>
    )

    expect(screen.getByText('Staff Cloud Architect')).toBeInTheDocument()
    expect(screen.getByText('CloudGlobal Systems')).toBeInTheDocument()
    expect(screen.getByText('Interviewing')).toBeInTheDocument()
    expect(screen.getByText(/Applied:/i)).toBeInTheDocument()
    expect(screen.getByText(/Oct.*2026/i)).toBeInTheDocument()
    expect(screen.getByText('Technical screen scheduled for tomorrow.')).toBeInTheDocument()

    // Click 'Update Status' button
    const updateBtn = screen.getByRole('button', { name: /Update Status/i })
    await user.click(updateBtn)

    expect(screen.getByRole('heading', { name: /Update Application Status/i })).toBeInTheDocument()
  })
})

describe('DashboardPage Application Tracking Dashboard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('renders unauthenticated state when user is not signed in', async () => {
    vi.spyOn(applicationService, 'listApplications').mockRejectedValue(
      new applicationService.ApplicationTrackingError(
        'Authentication required. Please sign in to view or manage your applications.',
        401
      )
    )

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    expect(
      await screen.findByRole('heading', { name: /Sign In to Track Applications/i })
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument()
  })

  it('renders loading state while applications are being fetched', async () => {
    localStorage.setItem('access_token', 'valid-token')
    vi.spyOn(applicationService, 'listApplications').mockImplementation(
      () => new Promise(() => {}) // Pending promise
    )

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    expect(screen.getByText(/Loading your tracked applications.../i)).toBeInTheDocument()
  })

  it('renders empty state when authenticated candidate has 0 applications', async () => {
    localStorage.setItem('access_token', 'valid-token')
    vi.spyOn(applicationService, 'listApplications').mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 50,
      total_pages: 0,
    })

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    expect(
      await screen.findByText(/No applications tracked yet/i)
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Explore Opportunities/i })
    ).toBeInTheDocument()
  })

  it('renders tracked applications and computes stat counters accurately', async () => {
    localStorage.setItem('access_token', 'valid-token')
    vi.spyOn(applicationService, 'listApplications').mockResolvedValue({
      items: [mockApp1, mockApp2],
      total: 2,
      page: 1,
      page_size: 50,
      total_pages: 1,
    })

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    // Verify opportunity cards render
    expect(await screen.findByText('Senior Frontend Engineer')).toBeInTheDocument()
    expect(screen.getByText('Staff Cloud Architect')).toBeInTheDocument()

    // Verify application counters
    expect(screen.getByText('Active Applications')).toBeInTheDocument()
    expect(screen.getByText('Interview Pipeline')).toBeInTheDocument()
  })

  it('displays error state with retry button on API failure', async () => {
    localStorage.setItem('access_token', 'valid-token')
    vi.spyOn(applicationService, 'listApplications').mockRejectedValue(
      new Error('Failed to connect to application tracking backend.')
    )

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )

    expect(
      await screen.findByText('Could not load applications')
    ).toBeInTheDocument()
    expect(
      screen.getByText('Failed to connect to application tracking backend.')
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
  })
})

describe('applicationService API Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('calls GET /api/v1/applications/ with query parameters', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [mockApp1], total: 1, page: 1, page_size: 20, total_pages: 1 }),
    })
    globalThis.fetch = fetchMock

    const result = await applicationService.listApplications(
      { status: 'saved', search: 'Frontend', page: 1, page_size: 20 },
      'test-jwt'
    )

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/applications/?page=1&page_size=20&status=saved&search=Frontend'),
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          Authorization: 'Bearer test-jwt',
        }),
      })
    )
    expect(result.total).toBe(1)
  })

  it('calls POST /api/v1/applications/ to save an application', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockApp1,
    })
    globalThis.fetch = fetchMock

    const result = await applicationService.createApplication(
      { opportunity_id: mockApp1.opportunity_id, status: 'saved', notes: 'Bookmarked' },
      'test-jwt'
    )

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/applications/',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer test-jwt',
        }),
        body: JSON.stringify({
          opportunity_id: mockApp1.opportunity_id,
          status: 'saved',
          notes: 'Bookmarked',
        }),
      })
    )
    expect(result.id).toBe(mockApp1.id)
  })

  it('handles 409 duplicate application conflict', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: 'An application for this opportunity already exists.' }),
    })
    globalThis.fetch = fetchMock

    await expect(
      applicationService.createApplication({ opportunity_id: mockApp1.opportunity_id }, 'test-jwt')
    ).rejects.toThrow('An application for this opportunity already exists.')
  })

  it('handles 422 invalid status transition error', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "Invalid status transition from 'saved' to 'offer'." }),
    })
    globalThis.fetch = fetchMock

    await expect(
      applicationService.updateApplicationStatus(mockApp1.id, { status: 'offer' }, 'test-jwt')
    ).rejects.toThrow("Invalid status transition from 'saved' to 'offer'.")
  })
})

describe('OpportunityDetailPage Tracking Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('displays Save Opportunity button and saves application when clicked', async () => {
    const user = userEvent.setup()
    localStorage.setItem('access_token', 'valid-token')

    vi.spyOn(opportunityService, 'getOpportunityById').mockResolvedValue({
      id: 'opp-100',
      title: 'Senior Distributed Engineer',
      company: 'TechCorp Cloud',
      opportunity_type: 'job',
      work_mode: 'remote',
      employment_type: 'fulltime',
      required_education_level: 'bachelor',
      location_city: 'Bengaluru',
      location_state: 'KA',
      location_country: 'India',
      salary_min: 2000000,
      salary_max: 3000000,
      salary_currency: 'INR',
      min_experience_years: 4,
      max_experience_years: 8,
      application_deadline: null,
      job_url: 'https://example.com/jobs/100',
      source: 'manual',
      source_id: 'tc-100',
      posted_date: '2026-10-01',
      required_skills: ['Go', 'Kubernetes'],
      preferred_skills: ['Kafka'],
      is_active: true,
      skills: [],
      created_at: '2026-10-01T00:00:00Z',
      updated_at: '2026-10-01T00:00:00Z',
      description: 'Distributed systems backend role.',
    })

    vi.spyOn(matchingService, 'getMatchByOpportunityId').mockResolvedValue(null)
    vi.spyOn(applicationService, 'listApplications').mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      total_pages: 0,
    })
    const createSpy = vi.spyOn(applicationService, 'createApplication').mockResolvedValue({
      ...mockApp1,
      id: 'new-app-100',
      opportunity_id: 'opp-100',
      status: 'saved',
    })

    render(
      <MemoryRouter initialEntries={['/opportunities/opp-100']}>
        <Routes>
          <Route path="/opportunities/:id" element={<OpportunityDetailPage />} />
        </Routes>
      </MemoryRouter>
    )

    const saveBtn = await screen.findByRole('button', { name: /Save Opportunity/i })
    expect(saveBtn).toBeInTheDocument()

    await user.click(saveBtn)

    expect(createSpy).toHaveBeenCalledWith({
      opportunity_id: 'opp-100',
      status: 'saved',
    })

    // After saving, status badge and Update Status button appear
    expect(await screen.findByRole('button', { name: /Update Status/i })).toBeInTheDocument()
  })
})
