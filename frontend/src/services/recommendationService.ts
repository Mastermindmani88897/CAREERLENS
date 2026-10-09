/**
 * Phase 18 Recommendation API Service.
 * Handles authenticated semantic opportunity recommendations via GET /api/v1/recommendations/
 */

import type {
  RecommendationFilterParams,
  RecommendationListResponse,
} from '@/types/recommendation'

/**
 * Custom error class for recommendations to capture specific status codes and messages.
 */
export class RecommendationError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'RecommendationError'
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

  if (response.status === 400) {
    return 'Candidate profile has insufficient content for recommendations. Please add skills, experience, or headline to your profile.'
  }
  if (response.status === 401) {
    return 'Authentication required. Please sign in to view your personalized recommendations.'
  }
  if (response.status === 404) {
    return 'Candidate profile not found. Please create a profile before requesting recommendations.'
  }
  if (response.status >= 500) {
    return 'Server error processing recommendations. Please try again later.'
  }
  return `Request failed with status ${response.status}.`
}

/**
 * Fetch paginated list of semantically ranked recommendations for the authenticated candidate.
 * Requires bearer access token (read from parameter or localStorage.getItem('access_token')).
 */
export async function getRecommendations(
  params: RecommendationFilterParams = {},
  token?: string
): Promise<RecommendationListResponse> {
  const query = new URLSearchParams()

  if (params.page) query.set('page', params.page.toString())
  if (params.page_size) query.set('page_size', params.page_size.toString())
  if (params.opportunity_type) query.set('opportunity_type', params.opportunity_type)
  if (params.work_mode) query.set('work_mode', params.work_mode)
  if (params.employment_type) query.set('employment_type', params.employment_type)
  if (params.location && params.location.trim()) query.set('location', params.location.trim())

  const authToken = token || localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }

  const queryString = query.toString()
  const endpoint = queryString ? `/api/v1/recommendations/?${queryString}` : '/api/v1/recommendations/'

  const response = await fetch(endpoint, {
    method: 'GET',
    headers,
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new RecommendationError(errorMsg, response.status)
  }

  return response.json()
}
