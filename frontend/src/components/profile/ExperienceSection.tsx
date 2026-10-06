import * as React from 'react'
import {
  AlertCircle,
  Briefcase,
  Building,
  Calendar,
  MapPin,
  Plus,
  Trash2,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type {
  EmploymentType,
  ExperienceCreate,
  ExperienceResponse,
  WorkMode,
} from '@/types/profile'

interface ExperienceSectionProps {
  experiences: ExperienceResponse[]
  onAddExperience: (payload: ExperienceCreate) => Promise<void>
  onDeleteExperience: (experienceId: string) => Promise<void>
}

export function ExperienceSection({
  experiences,
  onAddExperience,
  onDeleteExperience,
}: ExperienceSectionProps) {
  const [isAdding, setIsAdding] = React.useState(false)
  const [title, setTitle] = React.useState('')
  const [company, setCompany] = React.useState('')
  const [employmentType, setEmploymentType] = React.useState<EmploymentType>('fulltime')
  const [workMode, setWorkMode] = React.useState<WorkMode>('onsite')
  const [location, setLocation] = React.useState('')
  const [startDate, setStartDate] = React.useState('')
  const [endDate, setEndDate] = React.useState('')
  const [isCurrent, setIsCurrent] = React.useState(false)
  const [description, setDescription] = React.useState('')
  const [skillsInput, setSkillsInput] = React.useState('')

  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null)
  const [deletingId, setDeletingId] = React.useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)

    if (!title.trim() || !company.trim() || !startDate) {
      setErrorMsg('Job Title, Company Name, and Start Date are required.')
      return
    }

    if (!isCurrent && endDate && endDate < startDate) {
      setErrorMsg('End date cannot be earlier than start date.')
      return
    }

    const skillsUsed = skillsInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)

    try {
      setIsSubmitting(true)
      await onAddExperience({
        title: title.trim(),
        company: company.trim(),
        employment_type: employmentType,
        work_mode: workMode,
        location: location.trim() || null,
        start_date: startDate,
        end_date: isCurrent ? null : endDate || null,
        is_current: isCurrent,
        description: description.trim() || null,
        skills_used: skillsUsed,
      })
      // Reset form
      setTitle('')
      setCompany('')
      setLocation('')
      setStartDate('')
      setEndDate('')
      setIsCurrent(false)
      setDescription('')
      setSkillsInput('')
      setIsAdding(false)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to add experience.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      setDeletingId(id)
      await onDeleteExperience(id)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to delete experience.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle className="text-lg flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-primary" aria-hidden="true" />
            Work Experience ({experiences.length})
          </CardTitle>
          <CardDescription>
            Roles, corporate impact, key responsibilities, and technologies leveraged.
          </CardDescription>
        </div>

        <Button
          size="sm"
          variant={isAdding ? 'outline' : 'default'}
          onClick={() => {
            setIsAdding(!isAdding)
            setErrorMsg(null)
          }}
          data-testid="toggle-add-experience-btn"
        >
          {isAdding ? 'Cancel' : (
            <>
              <Plus className="mr-1.5 h-4 w-4" />
              Add Experience
            </>
          )}
        </Button>
      </CardHeader>

      <CardContent className="space-y-4">
        {errorMsg && (
          <div
            role="alert"
            className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-600 dark:text-red-400"
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {isAdding && (
          <form
            onSubmit={handleSubmit}
            className="rounded-lg border border-border bg-muted/30 p-4 space-y-4"
            data-testid="add-experience-form"
          >
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Add Work Experience
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="exp-title" className="text-xs font-medium text-foreground">
                  Job Title *
                </label>
                <Input
                  id="exp-title"
                  placeholder="e.g. Senior Software Engineer"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="exp-company" className="text-xs font-medium text-foreground">
                  Company Name *
                </label>
                <Input
                  id="exp-company"
                  placeholder="e.g. TechCorp Solutions"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label htmlFor="exp-emp-type" className="text-xs font-medium text-foreground">
                  Employment Type
                </label>
                <select
                  id="exp-emp-type"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={employmentType}
                  onChange={(e) => setEmploymentType(e.target.value as EmploymentType)}
                >
                  <option value="fulltime">Full-time</option>
                  <option value="parttime">Part-time</option>
                  <option value="internship">Internship</option>
                  <option value="contract">Contract</option>
                  <option value="any">Other / Any</option>
                </select>
              </div>

              <div className="space-y-1">
                <label htmlFor="exp-work-mode" className="text-xs font-medium text-foreground">
                  Work Mode
                </label>
                <select
                  id="exp-work-mode"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={workMode}
                  onChange={(e) => setWorkMode(e.target.value as WorkMode)}
                >
                  <option value="remote">Remote</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="onsite">Onsite</option>
                </select>
              </div>

              <div className="space-y-1">
                <label htmlFor="exp-location" className="text-xs font-medium text-foreground">
                  Location (City, State)
                </label>
                <Input
                  id="exp-location"
                  placeholder="e.g. Bengaluru, India"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="exp-start-date" className="text-xs font-medium text-foreground">
                  Start Date *
                </label>
                <Input
                  id="exp-start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="exp-end-date" className="text-xs font-medium text-foreground">
                  End Date
                </label>
                <Input
                  id="exp-end-date"
                  type="date"
                  disabled={isCurrent}
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="exp-current"
                checked={isCurrent}
                onChange={(e) => setIsCurrent(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <label htmlFor="exp-current" className="text-xs font-medium text-foreground cursor-pointer">
                I currently work here
              </label>
            </div>

            <div className="space-y-1">
              <label htmlFor="exp-description" className="text-xs font-medium text-foreground">
                Description / Key Responsibilities
              </label>
              <textarea
                id="exp-description"
                rows={3}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="Architected distributed APIs, managed CI/CD pipeline..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label htmlFor="exp-skills-used" className="text-xs font-medium text-foreground">
                Skills / Technologies Used (comma-separated)
              </label>
              <Input
                id="exp-skills-used"
                placeholder="Python, FastAPI, Docker, PostgreSQL"
                value={skillsInput}
                onChange={(e) => setSkillsInput(e.target.value)}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsAdding(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : 'Save Experience'}
              </Button>
            </div>
          </form>
        )}

        {experiences.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
            No work experience records added yet.
          </div>
        ) : (
          <div className="space-y-3" data-testid="experience-list">
            {experiences.map((exp) => (
              <div
                key={exp.id}
                className="flex items-start justify-between rounded-lg border border-border bg-card p-4 text-xs transition-colors hover:border-primary/40"
                data-testid={`experience-item-${exp.id}`}
              >
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="font-semibold text-sm text-foreground">
                      {exp.title}
                    </h4>
                    {exp.employment_type && (
                      <Badge variant="outline" className="text-[10px] capitalize">
                        {exp.employment_type}
                      </Badge>
                    )}
                    {exp.work_mode && (
                      <Badge variant="secondary" className="text-[10px] capitalize">
                        {exp.work_mode}
                      </Badge>
                    )}
                  </div>

                  <div className="flex items-center gap-3 text-muted-foreground">
                    <span className="flex items-center gap-1 font-medium">
                      <Building className="h-3.5 w-3.5 text-primary" />
                      {exp.company}
                    </span>
                    {exp.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {exp.location}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                    <Calendar className="h-3 w-3 text-primary" />
                    <span>
                      {exp.start_date} &ndash;{' '}
                      {exp.is_current ? 'Present' : exp.end_date || 'N/A'}
                    </span>
                  </div>

                  {exp.description && (
                    <p className="text-muted-foreground pt-1 leading-relaxed whitespace-pre-line">
                      {exp.description}
                    </p>
                  )}

                  {exp.skills_used && exp.skills_used.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {exp.skills_used.map((tech) => (
                        <span
                          key={tech}
                          className="rounded-md bg-muted px-2 py-0.5 text-[10px] font-medium text-foreground"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => handleDelete(exp.id)}
                  disabled={deletingId === exp.id}
                  className="text-muted-foreground hover:text-red-500 transition-colors p-1 rounded cursor-pointer"
                  title="Remove experience"
                  aria-label={`Remove ${exp.title}`}
                  data-testid={`delete-experience-${exp.id}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
