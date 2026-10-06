/**
 * Resume API service for Phase 11.
 * Handles resume uploads, deterministic parsed-result retrieval,
 * and client-side validation rules.
 */

import type { ResumeDetailResponse, ResumeResponse } from '@/types/resume'

export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 // 10 MB
export const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt']
export const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
]

export interface FileValidationResult {
  isValid: boolean
  error?: string
}

/**
 * Validate resume file extension and size prior to network dispatch.
 */
export function validateResumeFile(file: File): FileValidationResult {
  if (!file) {
    return { isValid: false, error: 'No file selected.' }
  }

  if (file.size === 0) {
    return {
      isValid: false,
      error: 'The selected file is empty (0 bytes). Please upload a valid resume.',
    }
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1)
    return {
      isValid: false,
      error: `File size (${sizeMb} MB) exceeds the maximum allowed limit of 10 MB.`,
    }
  }

  const filename = file.name.toLowerCase()
  const hasValidExt = ALLOWED_EXTENSIONS.some((ext) => filename.endsWith(ext))
  if (!hasValidExt) {
    return {
      isValid: false,
      error: 'Unsupported file format. Please upload a PDF (.pdf), Word document (.docx), or plain text (.txt) file.',
    }
  }

  return { isValid: true }
}

/**
 * Helper to extract safe error message from fetch responses.
 */
async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (data && typeof data.detail === 'string') {
      return data.detail
    }
    if (data && typeof data.message === 'string') {
      return data.message
    }
  } catch {
    // Non-JSON response
  }

  if (response.status === 401) {
    return 'Authentication required. Please sign in to upload your resume.'
  }
  if (response.status === 413) {
    return 'Uploaded file exceeds the maximum allowed size (10 MB).'
  }
  if (response.status === 422) {
    return 'The resume document could not be processed. Scanned PDFs or empty text are not supported.'
  }
  if (response.status >= 500) {
    return 'Server error while parsing resume. Please try again later.'
  }
  return `Upload request failed with status ${response.status}.`
}

/**
 * Upload resume file to the authenticated backend endpoint.
 */
export async function uploadResume(
  file: File,
  token?: string
): Promise<ResumeResponse> {
  const validation = validateResumeFile(file)
  if (!validation.isValid) {
    throw new Error(validation.error || 'Invalid resume file.')
  }

  const formData = new FormData()
  formData.append('file', file)

  const headers: Record<string, string> = {}
  const authToken = token || localStorage.getItem('access_token')
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }

  const response = await fetch('/api/v1/resumes/upload', {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    const errorMessage = await parseErrorMessage(response)
    throw new Error(errorMessage)
  }

  return response.json()
}

/**
 * Retrieve parsed resume details by ID.
 */
export async function getResume(
  resumeId: string,
  token?: string
): Promise<ResumeDetailResponse> {
  const headers: Record<string, string> = {}
  const authToken = token || localStorage.getItem('access_token')
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }

  const response = await fetch(`/api/v1/resumes/${resumeId}`, {
    method: 'GET',
    headers,
  })

  if (!response.ok) {
    const errorMessage = await parseErrorMessage(response)
    throw new Error(errorMessage)
  }

  return response.json()
}
