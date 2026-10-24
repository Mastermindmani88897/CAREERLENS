/**
 * Phase 21: Application Tracking and Status Transition Type Definitions
 */

export type ApplicationStatus =
  | 'saved'
  | 'applied'
  | 'oa'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'withdrawn';

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: 'Saved',
  applied: 'Applied',
  oa: 'Online Assessment',
  interview: 'Interviewing',
  offer: 'Offer Received',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
};

/**
 * Permitted status transitions according to the backend lifecycle state machine.
 */
export const PERMITTED_TRANSITIONS: Record<ApplicationStatus, ApplicationStatus[]> = {
  saved: ['applied', 'withdrawn'],
  applied: ['oa', 'interview', 'offer', 'rejected', 'withdrawn'],
  oa: ['interview', 'offer', 'rejected', 'withdrawn'],
  interview: ['interview', 'offer', 'rejected', 'withdrawn'],
  offer: ['rejected', 'withdrawn'],
  rejected: [],
  withdrawn: [],
};

export interface ApplicationOpportunitySummary {
  id: string;
  title: string;
  company: string;
  location_city?: string | null;
  location_state?: string | null;
  location_country?: string | null;
  work_mode?: string | null;
  employment_type?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  is_active: boolean;
}

export interface ApplicationStatusHistoryItem {
  id: string;
  application_id: string;
  status: ApplicationStatus;
  changed_at: string;
  notes?: string | null;
}

export interface ApplicationResponse {
  id: string;
  candidate_profile_id: string;
  opportunity_id: string;
  status: ApplicationStatus;
  applied_date?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  opportunity?: ApplicationOpportunitySummary | null;
  status_history?: ApplicationStatusHistoryItem[];
}

export interface ApplicationListResponse {
  items: ApplicationResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApplicationCreateRequest {
  opportunity_id: string;
  status?: ApplicationStatus;
  applied_date?: string | null;
  notes?: string | null;
}

export interface ApplicationStatusUpdateRequest {
  status: ApplicationStatus;
  notes?: string | null;
}

export interface ApplicationFilterParams {
  status?: ApplicationStatus | 'all';
  search?: string;
  page?: number;
  page_size?: number;
}
