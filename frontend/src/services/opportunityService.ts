/**
 * Phase 15 Opportunity API Service.
 * Handles public opportunity discovery queries and detail retrieval.
 */

import type {
  OpportunityDetail,
  OpportunityFilterParams,
  OpportunityListResponse,
} from '@/types/opportunity'

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

  if (response.status === 404) {
    return 'The requested opportunity was not found.'
  }
  if (response.status >= 500) {
    return 'Server error processing opportunity request. Please try again later.'
  }
  return `Request failed with status ${response.status}.`
}

/**
 * Fetch paginated list of opportunities with optional filters, search keyword, and sorting.
 * Public endpoint (does not require authentication, but attaches token if present in localStorage).
 */
export async function getOpportunities(
  params: OpportunityFilterParams = {}
): Promise<OpportunityListResponse> {
  const query = new URLSearchParams()

  if (params.page) query.set('page', params.page.toString())
  if (params.page_size) query.set('page_size', params.page_size.toString())
  if (params.opportunity_type) query.set('opportunity_type', params.opportunity_type)
  if (params.work_mode) query.set('work_mode', params.work_mode)
  if (params.employment_type) query.set('employment_type', params.employment_type)
  if (params.location && params.location.trim()) query.set('location', params.location.trim())
  if (params.min_experience_years !== undefined && params.min_experience_years !== '') {
    query.set('min_experience_years', params.min_experience_years.toString())
  }
  if (params.max_experience_years !== undefined && params.max_experience_years !== '') {
    query.set('max_experience_years', params.max_experience_years.toString())
  }
  if (params.keyword && params.keyword.trim()) {
    query.set('keyword', params.keyword.trim())
  }
  if (params.sort_by) query.set('sort_by', params.sort_by)

  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const queryString = query.toString()
  const endpoint = queryString ? `/api/v1/opportunities/?${queryString}` : '/api/v1/opportunities/'

  const response = await fetch(endpoint, {
    method: 'GET',
    headers,
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }

  return response.json()
}

/**
 * Fetch detailed view for a single opportunity by UUID, including relational skills.
 */
export async function getOpportunityById(id: string): Promise<OpportunityDetail> {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`/api/v1/opportunities/${id}`, {
    method: 'GET',
    headers,
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }

  return response.json()
}
