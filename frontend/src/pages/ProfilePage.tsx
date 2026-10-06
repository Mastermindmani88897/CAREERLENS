import * as React from 'react'
import {
  Compass,
  Sparkles,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { ErrorState } from '@/components/ui/error-state'
import { LoadingState } from '@/components/ui/loading-state'

import { BasicInfoSection } from '@/components/profile/BasicInfoSection'
import { CertificationsSection } from '@/components/profile/CertificationsSection'
import { EducationSection } from '@/components/profile/EducationSection'
import { ExperienceSection } from '@/components/profile/ExperienceSection'
import { PreferencesSection } from '@/components/profile/PreferencesSection'
import { ProfileHeader } from '@/components/profile/ProfileHeader'
import { ProjectsSection } from '@/components/profile/ProjectsSection'
import { ResumeSyncSection } from '@/components/profile/ResumeSyncSection'
import { SkillsSection } from '@/components/profile/SkillsSection'

import * as profileService from '@/services/profileService'
import type {
  CertificationCreate,
  EducationCreate,
  ExperienceCreate,
  ProfileDetailResponse,
  ProfileSyncResult,
  ProfileUpdate,
  ProjectCreate,
  SkillCreate,
} from '@/types/profile'

export function ProfilePage() {
  const [profile, setProfile] = React.useState<ProfileDetailResponse | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [isEditing, setIsEditing] = React.useState(false)

  const fetchProfile = React.useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await profileService.getMyProfile()
      setProfile(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load candidate profile.')
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    let ignore = false
    profileService
      .getMyProfile()
      .then((data) => {
        if (!ignore) {
          setProfile(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!ignore) {
          setError(err instanceof Error ? err.message : 'Failed to load candidate profile.')
          setLoading(false)
        }
      })
    return () => {
      ignore = true
    }
  }, [])

  // Profile update handler
  const handleUpdateProfile = async (payload: ProfileUpdate) => {
    await profileService.updateMyProfile(payload)
    await fetchProfile()
    setIsEditing(false)
  }

  // Skills handlers
  const handleAddSkill = async (payload: SkillCreate) => {
    await profileService.addSkill(payload)
    await fetchProfile()
  }

  const handleDeleteSkill = async (skillId: string) => {
    await profileService.deleteSkill(skillId)
    await fetchProfile()
  }

  // Education handlers
  const handleAddEducation = async (payload: EducationCreate) => {
    await profileService.addEducation(payload)
    await fetchProfile()
  }

  const handleDeleteEducation = async (educationId: string) => {
    await profileService.deleteEducation(educationId)
    await fetchProfile()
  }

  // Experience handlers
  const handleAddExperience = async (payload: ExperienceCreate) => {
    await profileService.addExperience(payload)
    await fetchProfile()
  }

  const handleDeleteExperience = async (experienceId: string) => {
    await profileService.deleteExperience(experienceId)
    await fetchProfile()
  }

  // Projects handlers
  const handleAddProject = async (payload: ProjectCreate) => {
    await profileService.addProject(payload)
    await fetchProfile()
  }

  const handleDeleteProject = async (projectId: string) => {
    await profileService.deleteProject(projectId)
    await fetchProfile()
  }

  // Certifications handlers
  const handleAddCertification = async (payload: CertificationCreate) => {
    await profileService.addCertification(payload)
    await fetchProfile()
  }

  const handleDeleteCertification = async (certificationId: string) => {
    await profileService.deleteCertification(certificationId)
    await fetchProfile()
  }

  // Resume Sync handler
  const handleSyncResume = async (resumeId: string): Promise<ProfileSyncResult> => {
    const result = await profileService.syncProfileFromResume(resumeId)
    await fetchProfile()
    return result
  }

  if (loading) {
    return (
      <div className="py-16" data-testid="profile-loading">
        <LoadingState message="Loading candidate career profile..." />
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="py-12" data-testid="profile-error">
        <ErrorState
          title="Unable to Load Profile"
          description={error || 'An unexpected error occurred while fetching your candidate profile.'}
          onRetry={fetchProfile}
        />
      </div>
    )
  }

  return (
    <div className="space-y-8 pb-16" data-testid="candidate-profile-page">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Candidate Profile
            </h1>
            <Badge variant="outline" className="text-xs font-medium">
              Phase 13
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            View, edit, and synchronize your career intelligence profile and preferences.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="text-xs py-1 px-2.5">
            <Sparkles className="mr-1.5 h-3.5 w-3.5 text-primary" aria-hidden="true" />
            Verified Profile API
          </Badge>
        </div>
      </div>

      {/* Profile Header */}
      <ProfileHeader
        profile={profile}
        isEditing={isEditing}
        onToggleEdit={() => setIsEditing(!isEditing)}
      />

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column (Main Details & Sub-resources) */}
        <div className="lg:col-span-8 space-y-8">
          {/* Basic Information */}
          <BasicInfoSection
            key={`info-${profile.updated_at}`}
            profile={profile}
            isEditing={isEditing}
            onUpdate={handleUpdateProfile}
          />

          {/* Career Preferences */}
          <PreferencesSection
            key={`pref-${profile.updated_at}`}
            profile={profile}
            isEditing={isEditing}
            onUpdate={handleUpdateProfile}
          />

          {/* Skills */}
          <SkillsSection
            skills={profile.skills || []}
            onAddSkill={handleAddSkill}
            onDeleteSkill={handleDeleteSkill}
          />

          {/* Experience */}
          <ExperienceSection
            experiences={profile.experiences || []}
            onAddExperience={handleAddExperience}
            onDeleteExperience={handleDeleteExperience}
          />

          {/* Education */}
          <EducationSection
            educations={profile.educations || []}
            onAddEducation={handleAddEducation}
            onDeleteEducation={handleDeleteEducation}
          />

          {/* Projects */}
          <ProjectsSection
            projects={profile.projects || []}
            onAddProject={handleAddProject}
            onDeleteProject={handleDeleteProject}
          />

          {/* Certifications */}
          <CertificationsSection
            certifications={profile.certifications || []}
            onAddCertification={handleAddCertification}
            onDeleteCertification={handleDeleteCertification}
          />
        </div>

        {/* Right Column (Resume Sync & Summary) */}
        <div className="lg:col-span-4 space-y-6">
          <ResumeSyncSection onSync={handleSyncResume} />

          <div className="rounded-xl border border-border bg-card p-5 text-xs text-muted-foreground space-y-3">
            <h4 className="font-semibold text-foreground text-sm flex items-center gap-2">
              <Compass className="h-4 w-4 text-primary" />
              Career Profile Highlights
            </h4>
            <div className="space-y-2">
              <div className="flex justify-between py-1 border-b border-border/60">
                <span>Total Skills:</span>
                <span className="font-semibold text-foreground">{profile.skills?.length || 0}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/60">
                <span>Work Experience:</span>
                <span className="font-semibold text-foreground">{profile.experiences?.length || 0} entries</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/60">
                <span>Education:</span>
                <span className="font-semibold text-foreground">{profile.educations?.length || 0} degrees</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/60">
                <span>Projects:</span>
                <span className="font-semibold text-foreground">{profile.projects?.length || 0} projects</span>
              </div>
              <div className="flex justify-between py-1">
                <span>Certifications:</span>
                <span className="font-semibold text-foreground">{profile.certifications?.length || 0} credentials</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
