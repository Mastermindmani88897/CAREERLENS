/**
 * Phase 20 Matching API Service.
 * Interfaces with backend endpoints at /api/v1/matches/
 * strictly reflecting backend Pydantic schemas.
 */

import type {
  MatchEvaluateRequest,
  MatchFilterParams,
  MatchListResponse,
  MatchResponse,
  MatchTriggerRequest,
} from '@/types/matching'

export class MatchingError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'MatchingError'
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
    return 'Authentication required. Please sign in to view or evaluate match scores.'
  }
  if (response.status === 404) {
    return 'No match evaluation found for this opportunity.'
  }
  if (response.status === 422) {
    return 'The requested opportunity is inactive or invalid for match evaluation.'
  }
  if (response.status >= 500) {
    return 'Server error processing match evaluation. Please try again later.'
  }
  return `Request failed with status ${response.status}.`
}

/**
 * Retrieve an existing match evaluation for an opportunity or match ID.
 * Returns null if no match has been computed yet (HTTP 404).
 */
export async function getMatchByOpportunityId(
  identifier: string,
  token?: string
): Promise<MatchResponse | null> {
  const authToken = token || localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }

  const response = await fetch(`/api/v1/matches/${identifier}`, {
    method: 'GET',
    headers,
  })

  if (response.status === 404) {
    return null
  }

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new MatchingError(errorMsg, response.status)
  }

  return response.json()
}

/**
 * Trigger an on-demand hybrid match evaluation for a single opportunity.
 * Idempotently computes and persists the match result.
 */
export async function triggerMatch(
  opportunityId: string,
  semanticSimilarity?: number,
  token?: string
): Promise<MatchResponse> {
  const authToken = token || localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }

  const payload: MatchTriggerRequest = {
    opportunity_id: opportunityId,
    ...(semanticSimilarity !== undefined ? { semantic_similarity: semanticSimilarity } : {}),
  }

  const response = await fetch('/api/v1/matches/', {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new MatchingError(errorMsg, response.status)
  }

  return response.json()
}

/**
 * Evaluate hybrid matches across opportunities (batch or active discovery, up to limit <= 100).
 */
export async function evaluateMatches(
  params: MatchEvaluateRequest = {},
  token?: string
): Promise<MatchListResponse> {
  const authToken = token || localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }

  const response = await fetch('/api/v1/matches/evaluate', {
    method: 'POST',
    headers,
    body: JSON.stringify(params),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new MatchingError(errorMsg, response.status)
  }

  return response.json()
}

/**
 * Retrieve paginated list of persisted match records for the authenticated candidate.
 */
export async function listMatches(
  params: MatchFilterParams = {},
  token?: string
): Promise<MatchListResponse> {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page.toString())
  if (params.page_size) query.set('page_size', params.page_size.toString())
  if (params.eligibility_status) query.set('eligibility_status', params.eligibility_status)
  if (params.min_score !== undefined && params.min_score !== '') {
    query.set('min_score', params.min_score.toString())
  }

  const authToken = token || localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }

  const queryString = query.toString()
  const endpoint = queryString ? `/api/v1/matches/?${queryString}` : '/api/v1/matches/'

  const response = await fetch(endpoint, {
    method: 'GET',
    headers,
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new MatchingError(errorMsg, response.status)
  }

  return response.json()
}
