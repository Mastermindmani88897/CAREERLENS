/**
 * TypeScript interface definitions for Phase 11 Resume Parsing and Ingestion.
 * Matches backend schemas from app/schemas/resume.py.
 */

export type ResumeStatus = 'uploaded' | 'processing' | 'parsed' | 'failed'

export interface ContactInfo {
  full_name?: string | null
  email?: string | null
  phone?: string | null
  linkedin_url?: string | null
  github_url?: string | null
  portfolio_url?: string | null
}

export interface ExtractedSkill {
  skill: string
  category?: string | null
  source_section: string
  evidence?: string | null
}

export interface ExtractedEducation {
  institution?: string | null
  degree?: string | null
  field_of_study?: string | null
  grade?: string | null
  start_year?: number | null
  end_year?: number | null
  evidence?: string | null
}

export interface ExtractedExperience {
  company?: string | null
  role?: string | null
  start_date?: string | null
  end_date?: string | null
  description?: string | null
  skills_used: string[]
  evidence?: string | null
}

export interface ExtractedProject {
  name: string
  description?: string | null
  technologies: string[]
  url?: string | null
  evidence?: string | null
}

export interface ExtractedCertification {
  name: string
  issuing_organization?: string | null
  issue_date?: string | null
  credential_url?: string | null
  evidence?: string | null
}

export interface ParsedResumeData {
  status: ResumeStatus
  contact: ContactInfo
  skills: ExtractedSkill[]
  education: ExtractedEducation[]
  experience: ExtractedExperience[]
  projects: ExtractedProject[]
  certifications: ExtractedCertification[]
  sections: Record<string, string>
  summary?: string | null
  raw_character_count: number
  normalized_character_count: number
  extracted_at: string
  error_message?: string | null
}

export interface ResumeResponse {
  id: string
  candidate_profile_id: string
  filename: string
  file_type: string
  file_size_bytes?: number | null
  status: ResumeStatus
  error_message?: string | null
  parsed_data?: ParsedResumeData | null
  created_at: string
}

export interface ResumeDetailResponse extends ResumeResponse {
  raw_text?: string | null
  parsed_json?: Record<string, unknown> | null
}
