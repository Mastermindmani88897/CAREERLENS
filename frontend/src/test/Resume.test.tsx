import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ResumeExtractionPreview } from '@/components/resume/ResumeExtractionPreview'
import { ResumeUploadCard } from '@/components/resume/ResumeUploadCard'
import { ResumePage } from '@/pages/ResumePage'
import * as resumeService from '@/services/resumeService'
import { renderWithRouter } from '@/test/test-utils'
import type { ResumeResponse } from '@/types/resume'

const mockParsedResume: ResumeResponse = {
  id: 'a1111111-1111-1111-1111-111111111111',
  candidate_profile_id: 'b2222222-2222-2222-2222-222222222222',
  filename: 'jordan_lee_resume.pdf',
  file_type: 'pdf',
  file_size_bytes: 10240,
  status: 'parsed',
  created_at: '2026-10-06T12:00:00Z',
  parsed_data: {
    status: 'parsed',
    contact: {
      full_name: 'Jordan Lee',
      email: 'jordan.lee@example.com',
      phone: '+1 555-0199',
      linkedin_url: 'https://linkedin.com/in/jordanlee',
      github_url: 'https://github.com/jordanlee',
      portfolio_url: 'https://jordanlee.dev',
    },
    skills: [
      {
        skill: 'Python',
        category: 'backend',
        source_section: 'skills',
        evidence: 'Python, FastAPI, Docker',
      },
      {
        skill: 'PostgreSQL',
        category: 'database',
        source_section: 'skills',
        evidence: 'PostgreSQL, Redis',
      },
    ],
    education: [
      {
        institution: 'University of Technology',
        degree: 'Bachelor of Science',
        field_of_study: 'Computer Science',
        grade: '3.8/4.0',
        start_year: 2018,
        end_year: 2022,
      },
    ],
    experience: [
      {
        role: 'Software Engineer',
        company: 'CloudTech Corp',
        start_date: '2022-06',
        end_date: 'Present',
        description: 'Developed scalable microservices and APIs.',
        skills_used: ['Python', 'FastAPI'],
      },
    ],
    projects: [
      {
        name: 'Distributed Task Queue',
        description: 'Asynchronous task runner built in Python.',
        technologies: ['Python', 'Redis'],
        url: 'https://github.com/jordanlee/task-queue',
      },
    ],
    certifications: [
      {
        name: 'AWS Certified Solutions Architect',
        issuing_organization: 'Amazon Web Services',
        issue_date: '2023',
        credential_url: 'https://aws.amazon.com/verify/12345',
      },
    ],
    sections: {
      contact: 'Jordan Lee jordan.lee@example.com',
      skills: 'Python, PostgreSQL',
    },
    summary: 'Experienced backend software engineer.',
    raw_character_count: 1200,
    normalized_character_count: 1150,
    extracted_at: '2026-10-06T12:00:05Z',
  },
}

describe('Phase 11 Resume Components and Pipeline', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('ResumeUploadCard Component', () => {
    it('1. renders upload dropzone and instruction text', () => {
      render(<ResumeUploadCard />)

      expect(
        screen.getByRole('heading', { name: /Resume Ingestion & Parsing/i })
      ).toBeInTheDocument()
      expect(
        screen.getByText(/Click to upload or drag and drop your resume/i)
      ).toBeInTheDocument()
      expect(
        screen.getByText(/Supported formats: PDF, DOCX, TXT/i)
      ).toBeInTheDocument()
    })

    it('2. validates and rejects unsupported file types', async () => {
      render(<ResumeUploadCard />)

      const fileInput = screen.getByTestId('resume-file-input')
      const invalidFile = new File(['binarycontent'], 'resume.exe', {
        type: 'application/x-msdownload',
      })

      fireEvent.change(fileInput, { target: { files: [invalidFile] } })

      expect(
        (await screen.findAllByText(/Unsupported file format/i)).length
      ).toBeGreaterThanOrEqual(1)
      expect(screen.queryByTestId('selected-file-preview')).not.toBeInTheDocument()
    })

    it('3. validates and rejects oversized files exceeding 10 MB limit', async () => {
      render(<ResumeUploadCard />)

      const fileInput = screen.getByTestId('resume-file-input')
      // 11 MB file
      const oversizedFile = new File(
        [new Uint8Array(11 * 1024 * 1024)],
        'giant_resume.pdf',
        { type: 'application/pdf' }
      )

      fireEvent.change(fileInput, { target: { files: [oversizedFile] } })

      expect(
        await screen.findByText(/exceeds the maximum allowed limit of 10 MB/i)
      ).toBeInTheDocument()
      expect(screen.queryByTestId('selected-file-preview')).not.toBeInTheDocument()
    })

    it('4. shows selected file preview and allows clearing file', async () => {
      render(<ResumeUploadCard />)

      const fileInput = screen.getByTestId('resume-file-input')
      const validFile = new File(['Sample resume text'], 'my_resume.txt', {
        type: 'text/plain',
      })

      fireEvent.change(fileInput, { target: { files: [validFile] } })

      expect(
        await screen.findByTestId('selected-file-preview')
      ).toBeInTheDocument()
      expect(screen.getByText('my_resume.txt')).toBeInTheDocument()

      const removeBtn = screen.getByRole('button', {
        name: /Remove selected file/i,
      })
      fireEvent.click(removeBtn)

      expect(screen.queryByTestId('selected-file-preview')).not.toBeInTheDocument()
    })

    it('5. triggers upload and renders loading state', async () => {
      let resolveUpload!: (value: ResumeResponse) => void
      const uploadPromise = new Promise<ResumeResponse>((resolve) => {
        resolveUpload = resolve
      })
      vi.spyOn(resumeService, 'uploadResume').mockReturnValue(uploadPromise)

      render(<ResumeUploadCard />)

      const fileInput = screen.getByTestId('resume-file-input')
      const validFile = new File(['Sample PDF content'], 'engineer.pdf', {
        type: 'application/pdf',
      })

      fireEvent.change(fileInput, { target: { files: [validFile] } })

      const uploadBtn = screen.getByTestId('upload-submit-button')
      fireEvent.click(uploadBtn)

      expect(
        await screen.findByText(/Extracting Resume.../i)
      ).toBeInTheDocument()
      expect(uploadBtn).toBeDisabled()

      // Resolve upload
      resolveUpload(mockParsedResume)
      await waitFor(() => {
        expect(screen.getByTestId('upload-success-banner')).toBeInTheDocument()
      })
    })

    it('6. shows upload success state and triggers onUploadSuccess callback', async () => {
      vi.spyOn(resumeService, 'uploadResume').mockResolvedValue(mockParsedResume)
      const onUploadSuccess = vi.fn()

      render(<ResumeUploadCard onUploadSuccess={onUploadSuccess} />)

      const fileInput = screen.getByTestId('resume-file-input')
      const validFile = new File(['Sample docx content'], 'resume.docx', {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      })

      fireEvent.change(fileInput, { target: { files: [validFile] } })

      const uploadBtn = screen.getByTestId('upload-submit-button')
      fireEvent.click(uploadBtn)

      expect(
        await screen.findByTestId('upload-success-banner')
      ).toBeInTheDocument()
      expect(
        screen.getByText(/Resume successfully parsed!/i)
      ).toBeInTheDocument()
      expect(onUploadSuccess).toHaveBeenCalledWith(mockParsedResume)
    })

    it('7. renders parsing error state when upload fails', async () => {
      vi.spyOn(resumeService, 'uploadResume').mockRejectedValue(
        new Error('Uploaded PDF file is malformed or corrupted.')
      )

      render(<ResumeUploadCard />)

      const fileInput = screen.getByTestId('resume-file-input')
      const validFile = new File(['corrupt data'], 'corrupt.pdf', {
        type: 'application/pdf',
      })

      fireEvent.change(fileInput, { target: { files: [validFile] } })

      const uploadBtn = screen.getByTestId('upload-submit-button')
      fireEvent.click(uploadBtn)

      expect(
        await screen.findByRole('alert')
      ).toBeInTheDocument()
      expect(
        screen.getByText(/Uploaded PDF file is malformed or corrupted./i)
      ).toBeInTheDocument()
    })

    it('8. supports retry action on upload error', async () => {
      const uploadMock = vi
        .spyOn(resumeService, 'uploadResume')
        .mockRejectedValueOnce(new Error('Server error while parsing resume.'))
        .mockResolvedValueOnce(mockParsedResume)

      render(<ResumeUploadCard />)

      const fileInput = screen.getByTestId('resume-file-input')
      const validFile = new File(['Valid content'], 'sample.txt', {
        type: 'text/plain',
      })

      fireEvent.change(fileInput, { target: { files: [validFile] } })

      const uploadBtn = screen.getByTestId('upload-submit-button')
      fireEvent.click(uploadBtn)

      const retryBtn = await screen.findByRole('button', { name: /Try Again/i })
      fireEvent.click(retryBtn)

      await waitFor(() => {
        expect(uploadMock).toHaveBeenCalledTimes(2)
      })
      expect(
        await screen.findByTestId('upload-success-banner')
      ).toBeInTheDocument()
    })
  })

  describe('ResumeExtractionPreview Component', () => {
    it('9. renders complete parsed details correctly', () => {
      render(<ResumeExtractionPreview resume={mockParsedResume} />)

      // Contact info
      expect(screen.getAllByText('Jordan Lee').length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('jordan.lee@example.com')).toBeInTheDocument()
      expect(screen.getByText('+1 555-0199')).toBeInTheDocument()
      expect(screen.getByText('LinkedIn')).toBeInTheDocument()
      expect(screen.getByText('GitHub')).toBeInTheDocument()
      expect(screen.getByText('Portfolio')).toBeInTheDocument()

      // Skills
      expect(screen.getAllByText(/Python/i).length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByText(/PostgreSQL/i).length).toBeGreaterThanOrEqual(1)

      // Education
      expect(
        screen.getByText(/University of Technology/i)
      ).toBeInTheDocument()
      expect(
        screen.getByText(/Bachelor of Science/i)
      ).toBeInTheDocument()
      expect(screen.getByText(/Grade\/CGPA: 3.8\/4.0/i)).toBeInTheDocument()

      // Experience
      expect(screen.getByText(/Software Engineer/i)).toBeInTheDocument()
      expect(screen.getByText(/CloudTech Corp/i)).toBeInTheDocument()

      // Projects
      expect(screen.getByText('Distributed Task Queue')).toBeInTheDocument()

      // Certifications
      expect(
        screen.getByText('AWS Certified Solutions Architect')
      ).toBeInTheDocument()
    })

    it('10. handles missing optional fields gracefully without crashing', () => {
      const minimalResume: ResumeResponse = {
        id: 'c3333333-3333-3333-3333-333333333333',
        candidate_profile_id: 'd4444444-4444-4444-4444-444444444444',
        filename: 'minimal.txt',
        file_type: 'txt',
        status: 'parsed',
        created_at: '2026-10-06T12:00:00Z',
        parsed_data: {
          status: 'parsed',
          contact: {
            full_name: null,
            email: null,
            phone: null,
            linkedin_url: null,
            github_url: null,
            portfolio_url: null,
          },
          skills: [],
          education: [],
          experience: [],
          projects: [],
          certifications: [],
          sections: {},
          raw_character_count: 50,
          normalized_character_count: 48,
          extracted_at: '2026-10-06T12:00:00Z',
        },
      }

      render(<ResumeExtractionPreview resume={minimalResume} />)

      expect(screen.getAllByText('minimal.txt').length).toBeGreaterThanOrEqual(1)
      expect(
        screen.getByText(/No specific skill matches detected/i)
      ).toBeInTheDocument()
      expect(
        screen.getByText(/No distinct experience entries detected/i)
      ).toBeInTheDocument()
      expect(
        screen.getByText(/No educational credentials detected/i)
      ).toBeInTheDocument()
    })
  })

  describe('ResumePage Integration', () => {
    it('11. renders page header, upload card, and displays extraction preview on upload', async () => {
      vi.spyOn(resumeService, 'uploadResume').mockResolvedValue(mockParsedResume)

      renderWithRouter(<ResumePage />)

      expect(
        screen.getByRole('heading', { name: /Resume Parsing & Intelligence/i })
      ).toBeInTheDocument()
      expect(
        screen.getByText(/Deterministic Extraction Guarantee/i)
      ).toBeInTheDocument()

      const fileInput = screen.getByTestId('resume-file-input')
      const validFile = new File(['content'], 'jordan_lee_resume.pdf', {
        type: 'application/pdf',
      })

      fireEvent.change(fileInput, { target: { files: [validFile] } })
      fireEvent.click(screen.getByTestId('upload-submit-button'))

      expect(
        await screen.findByRole('heading', {
          name: /Extracted Career Profile/i,
        })
      ).toBeInTheDocument()
      expect(screen.getAllByText('Jordan Lee').length).toBeGreaterThanOrEqual(1)
    })
  })
})
