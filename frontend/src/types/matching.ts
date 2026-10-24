/**
 * Phase 20 Hybrid Matching and Eligibility Type Definitions.
 * Strictly reflects backend Pydantic schemas in backend/app/schemas/matching.py
 * and PostgreSQL enums in backend/app/models/enums.py.
 */

export type EligibilityStatus = 'eligible' | 'partial' | 'review_required'

export interface SkillOverlapBreakdown {
  score: number
  required_count: number
  preferred_count: number
  matched_required: string[]
  missing_required: string[]
  matched_preferred: string[]
  missing_preferred: string[]
}

export interface ExperienceBreakdown {
  score: number
  candidate_total_years: number
  required_min_years: number | null
  required_max_years: number | null
  is_overqualified: boolean
  experience_gap_years: number
  warnings: string[]
}

export interface EducationBreakdown {
  score: number
  required_level: string
  candidate_highest_level: string
  meets_requirement: boolean
  missing_evidence: boolean
  warnings: string[]
}

export interface LocationBreakdown {
  score: number
  opportunity_location: string | null
  candidate_location: string | null
  open_to_relocation: boolean
  warnings: string[]
}

export interface WorkModeBreakdown {
  score: number
  opportunity_work_mode: string
  candidate_preferred_work_mode: string
  has_conflict: boolean
  warnings: string[]
}

export interface LocationWorkModeBreakdown {
  score: number
  opportunity_work_mode: string
  candidate_preferred_work_mode: string
  open_to_relocation: boolean
  warnings: string[]
}

export interface EmploymentTypeBreakdown {
  score: number
  opportunity_employment_type: string
  candidate_preferred_employment_type: string
  is_match: boolean
  is_missing: boolean
  warnings: string[]
}

export interface ScoringWeights {
  semantic_similarity: number
  skill_overlap: number
  experience: number
  education: number
  location: number
  work_mode: number
  location_work_mode: number
  employment_type: number
}

export interface ScoreBreakdown {
  weights: ScoringWeights
  skill_overlap: SkillOverlapBreakdown
  experience: ExperienceBreakdown
  education: EducationBreakdown
  location?: LocationBreakdown | null
  work_mode?: WorkModeBreakdown | null
  location_work_mode: LocationWorkModeBreakdown
  employment_type: EmploymentTypeBreakdown
  semantic_similarity_normalized: number
  semantic_similarity_raw: number
}

export interface MatchExplanation {
  strengths: string[]
  gaps: string[]
}

export interface SkillGap {
  matched_required_skills: string[]
  missing_required_skills: string[]
  matched_preferred_skills: string[]
  missing_preferred_skills: string[]
}

export interface MatchResponse {
  id: string
  candidate_profile_id: string
  opportunity_id: string
  semantic_score: number
  deterministic_score: number
  final_score: number
  eligibility_status: EligibilityStatus
  eligibility_warnings: string[] | null
  score_breakdown: ScoreBreakdown
  explanation: MatchExplanation
  skill_gap: SkillGap
  computed_at: string
}

export interface MatchSummaryResponse {
  id: string
  candidate_profile_id: string
  opportunity_id: string
  semantic_score: number
  deterministic_score: number
  final_score: number
  eligibility_status: EligibilityStatus
  eligibility_warnings: string[] | null
  computed_at: string
}

export interface MatchListResponse {
  items: MatchSummaryResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface MatchTriggerRequest {
  opportunity_id: string
  semantic_similarity?: number
}

export interface MatchEvaluateRequest {
  opportunity_ids?: string[]
  limit?: number
  semantic_similarity?: number
}

export interface MatchFilterParams {
  page?: number
  page_size?: number
  eligibility_status?: EligibilityStatus | ''
  min_score?: number | ''
}
