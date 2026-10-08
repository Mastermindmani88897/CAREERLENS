/**
 * Phase 15 Opportunity Discovery Type Definitions.
 * Mirrors backend Opportunity models, responses, and search/filter parameters.
 */

export type OpportunityType = 'job' | 'internship' | 'hackathon'
export type WorkMode = 'remote' | 'hybrid' | 'onsite' | 'any'
export type EmploymentType = 'fulltime' | 'parttime' | 'internship' | 'contract' | 'any'
export type EducationLevel = 'none' | 'diploma' | 'bachelor' | 'master' | 'phd' | 'any'

export type OpportunitySortBy =
  | 'newest'
  | 'oldest'
  | 'deadline_soonest'
  | 'title_asc'

export interface OpportunitySkill {
  id: string
  opportunity_id: string
  skill_name: string
  is_required: boolean
}

export interface Opportunity {
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
  application_deadline: string | null
  job_url: string | null
  source: string
  source_id: string | null
  posted_date: string | null
  required_skills: string[] | null
  preferred_skills: string[] | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface OpportunityDetail extends Opportunity {
  skills: OpportunitySkill[]
}

export interface OpportunityListResponse {
  items: Opportunity[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface OpportunityFilterParams {
  page?: number
  page_size?: number
  opportunity_type?: OpportunityType | ''
  work_mode?: WorkMode | ''
  employment_type?: EmploymentType | ''
  location?: string
  min_experience_years?: number | ''
  max_experience_years?: number | ''
  keyword?: string
  sort_by?: OpportunitySortBy
}
