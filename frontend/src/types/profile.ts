/**
 * TypeScript interface definitions for Phase 12/13 Candidate Profile.
 * Matches backend schemas from app/schemas/candidate_profile.py and enums from app/models/enums.py.
 */

export type WorkMode = 'remote' | 'hybrid' | 'onsite' | 'any'
export type EmploymentType = 'fulltime' | 'parttime' | 'internship' | 'contract' | 'any'
export type SkillCategory = 'technical' | 'soft' | 'tool' | 'language' | 'domain'
export type SkillProficiency = 'beginner' | 'intermediate' | 'advanced' | 'expert'
export type SkillSource = 'resume' | 'manual'
export type EducationLevel = 'none' | 'diploma' | 'bachelor' | 'master' | 'phd' | 'any'

// -----------------------------------------------------------------------------
// SUB-RESOURCE MODELS
// -----------------------------------------------------------------------------

export interface SkillBase {
  skill_name: string
  category?: SkillCategory | null
  proficiency_level?: SkillProficiency | null
  years_of_experience?: number | null
  source?: SkillSource
}

export interface SkillCreate extends SkillBase {}

export interface SkillResponse extends SkillBase {
  id: string
  candidate_profile_id: string
  created_at: string
}

export interface EducationBase {
  institution: string
  degree: string
  field_of_study: string
  education_level?: EducationLevel
  start_date?: string | null
  end_date?: string | null
  is_current?: boolean
  grade?: string | null
  description?: string | null
}

export interface EducationCreate extends EducationBase {}

export interface EducationResponse extends EducationBase {
  id: string
  candidate_profile_id: string
}

export interface ExperienceBase {
  company: string
  title: string
  employment_type?: EmploymentType | null
  location?: string | null
  work_mode?: WorkMode | null
  start_date: string
  end_date?: string | null
  is_current?: boolean
  description?: string | null
  skills_used?: string[]
}

export interface ExperienceCreate extends ExperienceBase {}

export interface ExperienceResponse extends ExperienceBase {
  id: string
  candidate_profile_id: string
  created_at: string
}

export interface ProjectBase {
  title: string
  description?: string | null
  technologies?: string[]
  project_url?: string | null
  repo_url?: string | null
  start_date?: string | null
  end_date?: string | null
}

export interface ProjectCreate extends ProjectBase {}

export interface ProjectResponse extends ProjectBase {
  id: string
  candidate_profile_id: string
  created_at: string
}

export interface CertificationBase {
  name: string
  issuing_organization: string
  issue_date?: string | null
  expiry_date?: string | null
  credential_id?: string | null
  credential_url?: string | null
}

export interface CertificationCreate extends CertificationBase {}

export interface CertificationResponse extends CertificationBase {
  id: string
  candidate_profile_id: string
  created_at: string
}

// -----------------------------------------------------------------------------
// CANDIDATE PROFILE MODELS
// -----------------------------------------------------------------------------

export interface ProfileBase {
  full_name: string
  headline?: string | null
  summary?: string | null
  phone?: string | null
  location_city?: string | null
  location_state?: string | null
  location_country?: string | null
  preferred_work_mode?: WorkMode
  preferred_employment_type?: EmploymentType
  preferred_salary_min?: number | null
  preferred_salary_max?: number | null
  preferred_salary_currency?: string | null
  open_to_relocation?: boolean
  linkedin_url?: string | null
  github_url?: string | null
  portfolio_url?: string | null
}

export interface ProfileCreate extends ProfileBase {}

export interface ProfileUpdate {
  full_name?: string | null
  headline?: string | null
  summary?: string | null
  phone?: string | null
  location_city?: string | null
  location_state?: string | null
  location_country?: string | null
  preferred_work_mode?: WorkMode | null
  preferred_employment_type?: EmploymentType | null
  preferred_salary_min?: number | null
  preferred_salary_max?: number | null
  preferred_salary_currency?: string | null
  open_to_relocation?: boolean | null
  linkedin_url?: string | null
  github_url?: string | null
  portfolio_url?: string | null
}

export interface ProfileResponse extends ProfileBase {
  id: string
  user_id: string
  created_at: string
  updated_at: string
}

export interface ProfileDetailResponse extends ProfileResponse {
  skills: SkillResponse[]
  educations: EducationResponse[]
  experiences: ExperienceResponse[]
  projects: ProjectResponse[]
  certifications: CertificationResponse[]
}

// -----------------------------------------------------------------------------
// RESUME SYNCHRONIZATION
// -----------------------------------------------------------------------------

export interface ProfileSyncResult {
  profile_id: string
  resume_id: string
  fields_updated: string[]
  skills_added: number
  educations_added: number
  experiences_added: number
  projects_added: number
  certifications_added: number
  preserved_fields: string[]
  message: string
}
