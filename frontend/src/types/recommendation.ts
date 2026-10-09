/**
 * Phase 18 Recommendations Type Definitions.
 * Strictly reflects the backend Pydantic schemas:
 * - SemanticOpportunityItem from backend/app/schemas/recommendation.py
 * - OpportunityResponse / enums from backend/app/schemas/opportunity.py & backend/app/models/enums.py
 * - RecommendationListResponse from backend/app/schemas/recommendation.py
 */

import type {
  EducationLevel,
  EmploymentType,
  OpportunityType,
  WorkMode,
} from '@/types/opportunity'

/**
 * Opportunity listing augmented with raw cosine semantic similarity score.
 * Reflects vector cosine alignment in [-1.0, 1.0].
 * It is not a hiring probability, overall job-fit percentage, or eligibility evaluation.
 */
export interface SemanticOpportunityItem {
  id: string
  title: string
  company: string
  description: string
  opportunity_type: OpportunityType
  employment_type: EmploymentType
  work_mode: WorkMode
  required_education_level: EducationLevel
  location_city: string | null
  location_state: string | null
  location_country: string | null
  salary_min: number | null
  salary_max: number | null
  salary_currency: string | null
  min_experience_years: number | null
  max_experience_years: number | null
  application_deadline: string | null // ISO date string (YYYY-MM-DD) or null
  job_url: string | null
  source: string
  source_id: string | null
  posted_date: string | null // ISO date string (YYYY-MM-DD) or null
  required_skills: string[] | null
  preferred_skills: string[] | null
  is_active: boolean
  created_at: string // ISO 8601 datetime string
  updated_at: string // ISO 8601 datetime string
  semantic_similarity: number // Raw cosine similarity in [-1.0, 1.0]
}

/**
 * Paginated collection of semantically retrieved opportunities.
 */
export interface RecommendationListResponse {
  items: SemanticOpportunityItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/**
 * Filter parameters supported by the backend recommendations endpoint
 * GET /api/v1/recommendations/
 */
export interface RecommendationFilterParams {
  page?: number
  page_size?: number
  opportunity_type?: OpportunityType | ''
  work_mode?: WorkMode | ''
  employment_type?: EmploymentType | ''
  location?: string
}
