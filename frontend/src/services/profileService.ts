/**
 * Candidate Profile API service for Phase 13.
 * Manages profile information, preferences, sub-resources (skills, education,
 * experience, projects, certifications), and resume synchronization.
 */

import type {
  CertificationCreate,
  CertificationResponse,
  EducationCreate,
  EducationResponse,
  ExperienceCreate,
  ExperienceResponse,
  ProfileDetailResponse,
  ProfileResponse,
  ProfileSyncResult,
  ProfileUpdate,
  ProjectCreate,
  ProjectResponse,
  SkillCreate,
  SkillResponse,
} from '@/types/profile'

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
      // Pydantic validation errors
      return data.detail.map((err: { msg?: string }) => err.msg || 'Validation error').join(', ')
    }
    if (data && typeof data.message === 'string') {
      return data.message
    }
  } catch {
    // Non-JSON response
  }

  if (response.status === 401) {
    return 'Authentication required. Please sign in to access your profile.'
  }
  if (response.status === 403) {
    return 'Permission denied. You can only access and synchronize your own resources.'
  }
  if (response.status === 404) {
    return 'The requested profile or item was not found.'
  }
  if (response.status === 409) {
    return 'A profile already exists for this candidate.'
  }
  if (response.status === 422) {
    return 'Validation failed. Please verify that all input fields are properly formatted.'
  }
  if (response.status >= 500) {
    return 'Server error processing profile request. Please try again later.'
  }
  return `Request failed with status ${response.status}.`
}

function getAuthHeaders(token?: string): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  const authToken = token || localStorage.getItem('access_token')
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }
  return headers
}

// -----------------------------------------------------------------------------
// PROFILE ROOT
// -----------------------------------------------------------------------------

/**
 * Fetch candidate profile with all sub-resources for the authenticated user.
 */
export async function getMyProfile(token?: string): Promise<ProfileDetailResponse> {
  const response = await fetch('/api/v1/profiles/me', {
    method: 'GET',
    headers: getAuthHeaders(token),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }

  return response.json()
}

/**
 * Update candidate profile fields and preferences.
 */
export async function updateMyProfile(
  payload: ProfileUpdate,
  token?: string
): Promise<ProfileResponse> {
  const response = await fetch('/api/v1/profiles/me', {
    method: 'PUT',
    headers: getAuthHeaders(token),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }

  return response.json()
}

/**
 * Synchronize candidate profile from an already parsed resume.
 */
export async function syncProfileFromResume(
  resumeId: string,
  token?: string
): Promise<ProfileSyncResult> {
  if (!resumeId || !resumeId.trim()) {
    throw new Error('A valid resume ID is required for synchronization.')
  }

  const response = await fetch(`/api/v1/profiles/me/sync-from-resume/${encodeURIComponent(resumeId.trim())}`, {
    method: 'POST',
    headers: getAuthHeaders(token),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }

  return response.json()
}

// -----------------------------------------------------------------------------
// SKILLS
// -----------------------------------------------------------------------------

export async function addSkill(
  payload: SkillCreate,
  token?: string
): Promise<SkillResponse> {
  const response = await fetch('/api/v1/profiles/me/skills', {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }

  return response.json()
}

export async function deleteSkill(
  skillId: string,
  token?: string
): Promise<void> {
  const response = await fetch(`/api/v1/profiles/me/skills/${encodeURIComponent(skillId)}`, {
    method: 'DELETE',
    headers: getAuthHeaders(token),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }
}

// -----------------------------------------------------------------------------
// EDUCATION
// -----------------------------------------------------------------------------

export async function addEducation(
  payload: EducationCreate,
  token?: string
): Promise<EducationResponse> {
  const response = await fetch('/api/v1/profiles/me/education', {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }

  return response.json()
}

export async function deleteEducation(
  educationId: string,
  token?: string
): Promise<void> {
  const response = await fetch(`/api/v1/profiles/me/education/${encodeURIComponent(educationId)}`, {
    method: 'DELETE',
    headers: getAuthHeaders(token),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }
}

// -----------------------------------------------------------------------------
// EXPERIENCE
// -----------------------------------------------------------------------------

export async function addExperience(
  payload: ExperienceCreate,
  token?: string
): Promise<ExperienceResponse> {
  const response = await fetch('/api/v1/profiles/me/experience', {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }

  return response.json()
}

export async function deleteExperience(
  experienceId: string,
  token?: string
): Promise<void> {
  const response = await fetch(`/api/v1/profiles/me/experience/${encodeURIComponent(experienceId)}`, {
    method: 'DELETE',
    headers: getAuthHeaders(token),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }
}

// -----------------------------------------------------------------------------
// PROJECTS
// -----------------------------------------------------------------------------

export async function addProject(
  payload: ProjectCreate,
  token?: string
): Promise<ProjectResponse> {
  const response = await fetch('/api/v1/profiles/me/projects', {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }

  return response.json()
}

export async function deleteProject(
  projectId: string,
  token?: string
): Promise<void> {
  const response = await fetch(`/api/v1/profiles/me/projects/${encodeURIComponent(projectId)}`, {
    method: 'DELETE',
    headers: getAuthHeaders(token),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }
}

// -----------------------------------------------------------------------------
// CERTIFICATIONS
// -----------------------------------------------------------------------------

export async function addCertification(
  payload: CertificationCreate,
  token?: string
): Promise<CertificationResponse> {
  const response = await fetch('/api/v1/profiles/me/certifications', {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }

  return response.json()
}

export async function deleteCertification(
  certificationId: string,
  token?: string
): Promise<void> {
  const response = await fetch(`/api/v1/profiles/me/certifications/${encodeURIComponent(certificationId)}`, {
    method: 'DELETE',
    headers: getAuthHeaders(token),
  })

  if (!response.ok) {
    const errorMsg = await parseErrorMessage(response)
    throw new Error(errorMsg)
  }
}
