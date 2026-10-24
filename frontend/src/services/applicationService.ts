/**
 * Phase 21 Application Tracking API Service.
 * Interfaces with backend endpoints at /api/v1/applications/
 * strictly reflecting backend Pydantic schemas and lifecycle state machine.
 */

import type {
  ApplicationCreateRequest,
  ApplicationFilterParams,
  ApplicationListResponse,
  ApplicationResponse,
  ApplicationStatusUpdateRequest,
} from '@/types/application'

export class ApplicationTrackingError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApplicationTrackingError'
    this.status = status
  }
}

/**
 * Helper to extract user-friendly error message from fetch responses.
 */
async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (data && typeof data.detail === 'string') {
      return data.detail
    }
    if (data && Array.isArray(data.detail)) {
      return data.detail.map((err: { msg?: string }) => err.msg || 'Validation error').join(', ')
    }
    if (data && typeof data.message === 'string') {
      return data.message
    }
  } catch {
    // Non-JSON response
  }

  if (response.status === 401) {
    return 'Authentication required. Please sign in to view or manage your applications.'
  }
  if (response.status === 404) {
    return 'The requested application was not found.'
  }
  if (response.status === 409) {
    return 'An application for this opportunity already exists in your tracked applications.'
  }
  if (response.status === 422) {
    return 'Invalid status transition or inactive opportunity.'
  }
  if (response.status >= 500) {
    return 'Server error processing application request. Please try again later.'
  }
  return `Request failed with status ${response.status}.`
}

function getAuthHeaders(token?: string): Record<string, string> {
  const authToken = token || localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }
  return headers
}

/**
 * Retrieve paginated list of candidate's tracked applications with optional status and search filters.
 */
export async function listApplications(
  params: ApplicationFilterParams = {},
  token?: string
): Promise<ApplicationListResponse> {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page.toString())
  if (params.page_size) query.set('page_size', params.page_size.toString())
  if (params.status && params.status !== 'all') query.set('status', params.status)
  if (params.search && params.search.trim()) query.set('search', params.search.trim())

  const queryString = query.toString() ? `?${query.toString()}` : ''
  const response = await fetch(`/api/v1/applications/${queryString}`, {
    method: 'GET',
    headers: getAuthHeaders(token),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new ApplicationTrackingError(errorMsg, response.status)
  }

  return response.json()
}

/**
 * Retrieve a single tracked application by its ID.
 */
export async function getApplicationById(
  applicationId: string,
  token?: string
): Promise<ApplicationResponse> {
  const response = await fetch(`/api/v1/applications/${applicationId}`, {
    method: 'GET',
    headers: getAuthHeaders(token),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new ApplicationTrackingError(errorMsg, response.status)
  }

  return response.json()
}

/**
 * Create or save an application for an opportunity.
 */
export async function createApplication(
  payload: ApplicationCreateRequest,
  token?: string
): Promise<ApplicationResponse> {
  const response = await fetch('/api/v1/applications/', {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new ApplicationTrackingError(errorMsg, response.status)
  }

  return response.json()
}

/**
 * Update the status of an application, strictly enforcing permitted transitions.
 */
export async function updateApplicationStatus(
  applicationId: string,
  payload: ApplicationStatusUpdateRequest,
  token?: string
): Promise<ApplicationResponse> {
  const response = await fetch(`/api/v1/applications/${applicationId}/status`, {
    method: 'PATCH',
    headers: getAuthHeaders(token),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new ApplicationTrackingError(errorMsg, response.status)
  }

  return response.json()
}

/**
 * Delete an application record owned by the candidate.
 */
export async function deleteApplication(
  applicationId: string,
  token?: string
): Promise<void> {
  const response = await fetch(`/api/v1/applications/${applicationId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(token),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new ApplicationTrackingError(errorMsg, response.status)
  }
}

/**
 * Fetch the permitted transitions matrix from the backend.
 */
export async function getPermittedTransitions(
  token?: string
): Promise<Record<string, string[]>> {
  const response = await fetch('/api/v1/applications/transitions', {
    method: 'GET',
    headers: getAuthHeaders(token),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new ApplicationTrackingError(errorMsg, response.status)
  }

  return response.json()
}
