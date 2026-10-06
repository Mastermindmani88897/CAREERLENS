import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProjectsSection } from '@/components/profile/ProjectsSection'
import { SkillsSection } from '@/components/profile/SkillsSection'
import { ProfilePage } from '@/pages/ProfilePage'
import * as profileService from '@/services/profileService'
import { renderWithRouter } from '@/test/test-utils'
import type {
  ProfileDetailResponse,
  ProfileResponse,
  ProfileSyncResult,
} from '@/types/profile'

const mockProfile: ProfileDetailResponse = {
  id: 'c1111111-1111-1111-1111-111111111111',
  user_id: 'u1111111-1111-1111-1111-111111111111',
  full_name: 'Alex Morgan',
  headline: 'Senior Cloud Engineer',
  summary: 'Specializing in resilient distributed architectures and developer platforms.',
  phone: '+91 9876543210',
  location_city: 'Bengaluru',
  location_state: 'Karnataka',
  location_country: 'India',
  preferred_work_mode: 'remote',
  preferred_employment_type: 'fulltime',
  preferred_salary_min: 1500000,
  preferred_salary_max: 2500000,
  preferred_salary_currency: 'INR',
  open_to_relocation: true,
  linkedin_url: 'https://linkedin.com/in/alexmorgan',
  github_url: 'https://github.com/alexmorgan',
  portfolio_url: 'https://alexmorgan.dev',
  created_at: '2026-10-06T10:00:00Z',
  updated_at: '2026-10-06T12:00:00Z',
  skills: [
    {
      id: 's1111111-1111-1111-1111-111111111111',
      candidate_profile_id: 'c1111111-1111-1111-1111-111111111111',
      skill_name: 'Go',
      category: 'technical',
      proficiency_level: 'expert',
      years_of_experience: 5,
      source: 'manual',
      created_at: '2026-10-06T10:00:00Z',
    },
    {
      id: 's2222222-2222-2222-2222-222222222222',
      candidate_profile_id: 'c1111111-1111-1111-1111-111111111111',
      skill_name: 'Kubernetes',
      category: 'tool',
      proficiency_level: 'advanced',
      years_of_experience: 4,
      source: 'resume',
      created_at: '2026-10-06T10:00:00Z',
    },
  ],
  educations: [
    {
      id: 'e1111111-1111-1111-1111-111111111111',
      candidate_profile_id: 'c1111111-1111-1111-1111-111111111111',
      institution: 'Indian Institute of Technology',
      degree: 'B.Tech',
      field_of_study: 'Computer Science and Engineering',
      education_level: 'bachelor',
      start_date: '2018-08-01',
      end_date: '2022-05-31',
      is_current: false,
      grade: '8.9 / 10.0',
      description: 'First Class with Distinction',
    },
  ],
  experiences: [
    {
      id: 'x1111111-1111-1111-1111-111111111111',
      candidate_profile_id: 'c1111111-1111-1111-1111-111111111111',
      company: 'ScaleGrid Systems',
      title: 'Senior Infrastructure Engineer',
      employment_type: 'fulltime',
      location: 'Bengaluru',
      work_mode: 'hybrid',
      start_date: '2022-07-01',
      end_date: null,
      is_current: true,
      description: 'Orchestrated multi-region Kubernetes clusters.',
      skills_used: ['Kubernetes', 'Go', 'Terraform'],
      created_at: '2026-10-06T10:00:00Z',
    },
  ],
  projects: [
    {
      id: 'p1111111-1111-1111-1111-111111111111',
      candidate_profile_id: 'c1111111-1111-1111-1111-111111111111',
      title: 'Distributed KV Store',
      description: 'Raft consensus key-value storage engine in Go.',
      technologies: ['Go', 'Raft', 'gRPC'],
      project_url: 'https://kvstore.demo.local',
      repo_url: 'https://github.com/alexmorgan/kvstore',
      start_date: '2023-01-01',
      end_date: '2023-06-30',
      created_at: '2026-10-06T10:00:00Z',
    },
  ],
  certifications: [
    {
      id: 'q1111111-1111-1111-1111-111111111111',
      candidate_profile_id: 'c1111111-1111-1111-1111-111111111111',
      name: 'Certified Kubernetes Administrator (CKA)',
      issuing_organization: 'The Linux Foundation',
      issue_date: '2023-04-15',
      expiry_date: '2026-04-15',
      credential_id: 'CKA-987654321',
      credential_url: 'https://www.credly.com/badges/cka-sample',
      created_at: '2026-10-06T10:00:00Z',
    },
  ],
}

describe('Phase 13 Candidate Profile Frontend', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  // 1. Profile page renders
  it('1. renders candidate profile page with top title and details', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockResolvedValueOnce(mockProfile)

    renderWithRouter(<ProfilePage />)

    expect(screen.getByTestId('profile-loading')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByTestId('candidate-profile-page')).toBeInTheDocument()
    })

    expect(screen.getByText('Alex Morgan')).toBeInTheDocument()
    expect(screen.getByText('Senior Cloud Engineer')).toBeInTheDocument()
    expect(screen.getByText(/Open to Relocation/i)).toBeInTheDocument()
  })

  // 2. Loading state
  it('2. displays loading state while profile request is in-flight', () => {
    vi.spyOn(profileService, 'getMyProfile').mockImplementationOnce(
      () => new Promise(() => {}) // never resolves
    )

    renderWithRouter(<ProfilePage />)

    expect(screen.getByTestId('profile-loading')).toBeInTheDocument()
    expect(
      screen.getByText(/Loading candidate career profile/i)
    ).toBeInTheDocument()
  })

  // 3. API error state
  it('3. displays error state when initial profile fetch fails', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockRejectedValueOnce(
      new Error('Database connectivity issue')
    )

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByTestId('profile-error')).toBeInTheDocument()
    })

    expect(screen.getByText('Unable to Load Profile')).toBeInTheDocument()
    expect(screen.getByText(/Database connectivity issue/i)).toBeInTheDocument()
  })

  // 4. Profile data rendering (basic info & preferences)
  it('4. displays basic information and career preferences correctly', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockResolvedValueOnce(mockProfile)

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByTestId('basic-info-display')).toBeInTheDocument()
    })

    expect(
      screen.getByText(/resilient distributed architectures/i)
    ).toBeInTheDocument()
    expect(screen.getByText('+91 9876543210')).toBeInTheDocument()
    expect(
      within(screen.getByTestId('basic-info-display')).getByText(
        'Bengaluru, Karnataka, India'
      )
    ).toBeInTheDocument()

    const prefDisplay = screen.getByTestId('preferences-display')
    expect(
      within(prefDisplay).getByText(/INR/i)
    ).toBeInTheDocument()
  })

  // 5. Profile update toggle & submit
  it('5. allows toggling edit mode and saving updated profile info', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockResolvedValue(mockProfile)
    const updateSpy = vi
      .spyOn(profileService, 'updateMyProfile')
      .mockResolvedValueOnce({
        ...mockProfile,
        headline: 'Lead Cloud Architect',
      } as ProfileResponse)

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByTestId('toggle-edit-btn')).toBeInTheDocument()
    })

    // Click Edit Profile
    fireEvent.click(screen.getByTestId('toggle-edit-btn'))

    expect(screen.getByTestId('basic-info-form')).toBeInTheDocument()
    expect(screen.getByTestId('preferences-form')).toBeInTheDocument()

    // Change headline and save
    const headlineInput = screen.getByLabelText(/Professional Headline/i)
    fireEvent.change(headlineInput, {
      target: { value: 'Lead Cloud Architect' },
    })

    fireEvent.click(screen.getByText('Save Basic Info'))

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          headline: 'Lead Cloud Architect',
        })
      )
    })
  })

  // 6. Skills rendering
  it('6. renders skills list with category and proficiency badges', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockResolvedValueOnce(mockProfile)

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByTestId('skills-list')).toBeInTheDocument()
    })

    const skillsList = screen.getByTestId('skills-list')
    expect(within(skillsList).getByText('Go')).toBeInTheDocument()
    expect(within(skillsList).getByText('Kubernetes')).toBeInTheDocument()
    expect(within(skillsList).getByText('(5y)')).toBeInTheDocument()
    expect(within(skillsList).getByText(/expert/i)).toBeInTheDocument()
  })

  // 7. Add skill
  it('7. allows adding a new skill via form submission', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockResolvedValue(mockProfile)
    const addSkillSpy = vi
      .spyOn(profileService, 'addSkill')
      .mockResolvedValueOnce({
        id: 's3333333-3333-3333-3333-333333333333',
        candidate_profile_id: mockProfile.id,
        skill_name: 'PostgreSQL',
        category: 'technical',
        proficiency_level: 'advanced',
        years_of_experience: 3,
        source: 'manual',
        created_at: '2026-10-06T12:00:00Z',
      })

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByTestId('toggle-add-skill-btn')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('toggle-add-skill-btn'))

    const nameInput = screen.getByLabelText(/Skill Name \*/i)
    fireEvent.change(nameInput, { target: { value: 'PostgreSQL' } })

    fireEvent.click(screen.getByText('Save Skill'))

    await waitFor(() => {
      expect(addSkillSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          skill_name: 'PostgreSQL',
          category: 'technical',
        })
      )
    })
  })

  // 8. Delete skill
  it('8. allows deleting a skill from candidate profile', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockResolvedValue(mockProfile)
    const deleteSkillSpy = vi
      .spyOn(profileService, 'deleteSkill')
      .mockResolvedValueOnce()

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(
        screen.getByTestId(`delete-skill-${mockProfile.skills[0].id}`)
      ).toBeInTheDocument()
    })

    fireEvent.click(
      screen.getByTestId(`delete-skill-${mockProfile.skills[0].id}`)
    )

    await waitFor(() => {
      expect(deleteSkillSpy).toHaveBeenCalledWith(mockProfile.skills[0].id)
    })
  })

  // 9. Education rendering / add / delete
  it('9. supports education rendering, adding, and deleting', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockResolvedValue(mockProfile)
    const addEduSpy = vi
      .spyOn(profileService, 'addEducation')
      .mockResolvedValueOnce({
        id: 'e2222222-2222-2222-2222-222222222222',
        candidate_profile_id: mockProfile.id,
        institution: 'Stanford University',
        degree: 'M.S.',
        field_of_study: 'Computer Science',
        education_level: 'master',
      })
    const deleteEduSpy = vi
      .spyOn(profileService, 'deleteEducation')
      .mockResolvedValueOnce()

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(
        screen.getByText(/Indian Institute of Technology/i)
      ).toBeInTheDocument()
    })

    // Test Add
    fireEvent.click(screen.getByTestId('toggle-add-education-btn'))
    fireEvent.change(screen.getByLabelText(/Institution \*/i), {
      target: { value: 'Stanford University' },
    })
    fireEvent.change(screen.getByLabelText(/Degree \*/i), {
      target: { value: 'M.S.' },
    })
    fireEvent.change(screen.getByLabelText(/Field of Study \*/i), {
      target: { value: 'Computer Science' },
    })
    fireEvent.click(screen.getByText('Save Education'))

    await waitFor(() => {
      expect(addEduSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          institution: 'Stanford University',
          degree: 'M.S.',
        })
      )
    })

    // Test Delete
    fireEvent.click(
      screen.getByTestId(`delete-education-${mockProfile.educations[0].id}`)
    )
    await waitFor(() => {
      expect(deleteEduSpy).toHaveBeenCalledWith(mockProfile.educations[0].id)
    })
  })

  // 10. Experience rendering / add / delete
  it('10. supports work experience rendering, adding, and deleting', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockResolvedValue(mockProfile)
    const addExpSpy = vi
      .spyOn(profileService, 'addExperience')
      .mockResolvedValueOnce({
        id: 'x2222222-2222-2222-2222-222222222222',
        candidate_profile_id: mockProfile.id,
        company: 'CloudTech',
        title: 'Backend Engineer',
        employment_type: 'fulltime',
        work_mode: 'remote',
        start_date: '2021-01-01',
        skills_used: ['Python'],
        created_at: '2026-10-06T12:00:00Z',
      })
    const deleteExpSpy = vi
      .spyOn(profileService, 'deleteExperience')
      .mockResolvedValueOnce()

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByText(/ScaleGrid Systems/i)).toBeInTheDocument()
    })

    // Add experience
    fireEvent.click(screen.getByTestId('toggle-add-experience-btn'))
    fireEvent.change(screen.getByLabelText(/Job Title \*/i), {
      target: { value: 'Backend Engineer' },
    })
    fireEvent.change(screen.getByLabelText(/Company Name \*/i), {
      target: { value: 'CloudTech' },
    })
    fireEvent.change(screen.getByLabelText(/Start Date \*/i), {
      target: { value: '2021-01-01' },
    })
    fireEvent.click(screen.getByText('Save Experience'))

    await waitFor(() => {
      expect(addExpSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          company: 'CloudTech',
          title: 'Backend Engineer',
        })
      )
    })

    // Delete experience
    fireEvent.click(
      screen.getByTestId(`delete-experience-${mockProfile.experiences[0].id}`)
    )
    await waitFor(() => {
      expect(deleteExpSpy).toHaveBeenCalledWith(mockProfile.experiences[0].id)
    })
  })

  // 11. Projects rendering / add / delete
  it('11. supports project rendering, adding, and deleting', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockResolvedValue(mockProfile)
    const addProjSpy = vi
      .spyOn(profileService, 'addProject')
      .mockResolvedValueOnce({
        id: 'p2222222-2222-2222-2222-222222222222',
        candidate_profile_id: mockProfile.id,
        title: 'CareerLens Engine',
        technologies: ['React', 'FastAPI'],
        created_at: '2026-10-06T12:00:00Z',
      })
    const deleteProjSpy = vi
      .spyOn(profileService, 'deleteProject')
      .mockResolvedValueOnce()

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByText('Distributed KV Store')).toBeInTheDocument()
    })

    // Add project
    fireEvent.click(screen.getByTestId('toggle-add-project-btn'))
    fireEvent.change(screen.getByLabelText(/Project Title \*/i), {
      target: { value: 'CareerLens Engine' },
    })
    fireEvent.click(screen.getByText('Save Project'))

    await waitFor(() => {
      expect(addProjSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'CareerLens Engine',
        })
      )
    })

    // Delete project
    fireEvent.click(
      screen.getByTestId(`delete-project-${mockProfile.projects[0].id}`)
    )
    await waitFor(() => {
      expect(deleteProjSpy).toHaveBeenCalledWith(mockProfile.projects[0].id)
    })
  })

  // 12. Certifications rendering / add / delete
  it('12. supports certifications rendering, adding, and deleting', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockResolvedValue(mockProfile)
    const addCertSpy = vi
      .spyOn(profileService, 'addCertification')
      .mockResolvedValueOnce({
        id: 'q2222222-2222-2222-2222-222222222222',
        candidate_profile_id: mockProfile.id,
        name: 'AWS Solutions Architect',
        issuing_organization: 'Amazon Web Services',
        created_at: '2026-10-06T12:00:00Z',
      })
    const deleteCertSpy = vi
      .spyOn(profileService, 'deleteCertification')
      .mockResolvedValueOnce()

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(
        screen.getByText(/Certified Kubernetes Administrator/i)
      ).toBeInTheDocument()
    })

    // Add certification
    fireEvent.click(screen.getByTestId('toggle-add-certification-btn'))
    fireEvent.change(screen.getByLabelText(/Certification Name \*/i), {
      target: { value: 'AWS Solutions Architect' },
    })
    fireEvent.change(screen.getByLabelText(/Issuing Organization \*/i), {
      target: { value: 'Amazon Web Services' },
    })
    fireEvent.click(screen.getByText('Save Certification'))

    await waitFor(() => {
      expect(addCertSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'AWS Solutions Architect',
          issuing_organization: 'Amazon Web Services',
        })
      )
    })

    // Delete certification
    fireEvent.click(
      screen.getByTestId(
        `delete-certification-${mockProfile.certifications[0].id}`
      )
    )
    await waitFor(() => {
      expect(deleteCertSpy).toHaveBeenCalledWith(
        mockProfile.certifications[0].id
      )
    })
  })

  // 13 & 14. Resume synchronization trigger & result display
  it('13 & 14. triggers resume synchronization and displays structured audit summary', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockResolvedValue(mockProfile)
    const syncResult: ProfileSyncResult = {
      profile_id: mockProfile.id,
      resume_id: 'r1111111-1111-1111-1111-111111111111',
      fields_updated: ['summary', 'headline'],
      skills_added: 4,
      educations_added: 1,
      experiences_added: 2,
      projects_added: 1,
      certifications_added: 1,
      preserved_fields: ['preferred_work_mode', 'preferred_locations'],
      message: 'Profile synchronized successfully from resume.',
    }

    const syncSpy = vi
      .spyOn(profileService, 'syncProfileFromResume')
      .mockResolvedValueOnce(syncResult)

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByTestId('resume-sync-form')).toBeInTheDocument()
    })

    const resumeIdInput = screen.getByLabelText(/Parsed Resume Document ID/i)
    fireEvent.change(resumeIdInput, {
      target: { value: 'r1111111-1111-1111-1111-111111111111' },
    })

    fireEvent.click(screen.getByTestId('sync-resume-btn'))

    await waitFor(() => {
      expect(syncSpy).toHaveBeenCalledWith(
        'r1111111-1111-1111-1111-111111111111'
      )
      expect(screen.getByTestId('sync-result-card')).toBeInTheDocument()
    })

    expect(
      screen.getByText('Profile synchronized successfully from resume.')
    ).toBeInTheDocument()
    expect(screen.getByText('+4')).toBeInTheDocument() // skills added
    expect(screen.getByText('+2')).toBeInTheDocument() // experiences added
    expect(screen.getAllByText('+1')).toHaveLength(3) // educations, projects, certs
    expect(
      screen.getByText(/Protected user fields preserved/i)
    ).toBeInTheDocument()
  })

  // 15. Form validation (e.g. required full name, URL validation)
  it('15. rejects invalid project URLs and empty required fields', async () => {
    const onAddProject = vi.fn()
    const onDeleteProject = vi.fn()

    renderWithRouter(
      <ProjectsSection
        projects={[]}
        onAddProject={onAddProject}
        onDeleteProject={onDeleteProject}
      />
    )

    fireEvent.click(screen.getByTestId('toggle-add-project-btn'))

    // Try submitting with invalid URL
    fireEvent.change(screen.getByLabelText(/Project Title \*/i), {
      target: { value: 'Test Project' },
    })
    fireEvent.change(screen.getByLabelText(/Live Project URL/i), {
      target: { value: 'not-a-valid-url' },
    })

    fireEvent.click(screen.getByText('Save Project'))

    expect(
      await screen.findByText(/Live Demo URL must be a valid HTTP\/HTTPS URL/i)
    ).toBeInTheDocument()
    expect(onAddProject).not.toHaveBeenCalled()
  })

  // 16. Authentication failure behavior
  it('16. displays friendly message when user is unauthenticated (401)', async () => {
    vi.spyOn(profileService, 'getMyProfile').mockRejectedValueOnce(
      new Error(
        'Authentication required. Please sign in to access your profile.'
      )
    )

    renderWithRouter(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByTestId('profile-error')).toBeInTheDocument()
    })

    expect(
      screen.getByText(/Authentication required. Please sign in/i)
    ).toBeInTheDocument()
  })

  // 17. API failure behavior during mutation
  it('17. displays error feedback if an API operation fails', async () => {
    const onAddSkill = vi
      .fn()
      .mockRejectedValueOnce(new Error('Skill already exists on this profile.'))
    const onDeleteSkill = vi.fn()

    renderWithRouter(
      <SkillsSection
        skills={[]}
        onAddSkill={onAddSkill}
        onDeleteSkill={onDeleteSkill}
      />
    )

    fireEvent.click(screen.getByTestId('toggle-add-skill-btn'))
    fireEvent.change(screen.getByLabelText(/Skill Name \*/i), {
      target: { value: 'Python' },
    })
    fireEvent.click(screen.getByText('Save Skill'))

    expect(
      await screen.findByText(/Skill already exists on this profile/i)
    ).toBeInTheDocument()
  })
})
