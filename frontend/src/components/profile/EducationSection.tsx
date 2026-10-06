import * as React from 'react'
import {
  AlertCircle,
  Calendar,
  GraduationCap,
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
  EducationCreate,
  EducationLevel,
  EducationResponse,
} from '@/types/profile'

interface EducationSectionProps {
  educations: EducationResponse[]
  onAddEducation: (payload: EducationCreate) => Promise<void>
  onDeleteEducation: (educationId: string) => Promise<void>
}

export function EducationSection({
  educations,
  onAddEducation,
  onDeleteEducation,
}: EducationSectionProps) {
  const [isAdding, setIsAdding] = React.useState(false)
  const [institution, setInstitution] = React.useState('')
  const [degree, setDegree] = React.useState('')
  const [fieldOfStudy, setFieldOfStudy] = React.useState('')
  const [educationLevel, setEducationLevel] = React.useState<EducationLevel>('bachelor')
  const [startDate, setStartDate] = React.useState('')
  const [endDate, setEndDate] = React.useState('')
  const [isCurrent, setIsCurrent] = React.useState(false)
  const [grade, setGrade] = React.useState('')
  const [description, setDescription] = React.useState('')

  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null)
  const [deletingId, setDeletingId] = React.useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)

    if (!institution.trim() || !degree.trim() || !fieldOfStudy.trim()) {
      setErrorMsg('Institution, Degree, and Field of Study are required.')
      return
    }

    if (startDate && endDate && endDate < startDate) {
      setErrorMsg('End date cannot be earlier than start date.')
      return
    }

    try {
      setIsSubmitting(true)
      await onAddEducation({
        institution: institution.trim(),
        degree: degree.trim(),
        field_of_study: fieldOfStudy.trim(),
        education_level: educationLevel,
        start_date: startDate || null,
        end_date: isCurrent ? null : endDate || null,
        is_current: isCurrent,
        grade: grade.trim() || null,
        description: description.trim() || null,
      })
      // Reset form
      setInstitution('')
      setDegree('')
      setFieldOfStudy('')
      setStartDate('')
      setEndDate('')
      setIsCurrent(false)
      setGrade('')
      setDescription('')
      setIsAdding(false)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to add education.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      setDeletingId(id)
      await onDeleteEducation(id)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to delete education.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle className="text-lg flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-primary" aria-hidden="true" />
            Education ({educations.length})
          </CardTitle>
          <CardDescription>
            Degrees, academic background, fields of study, and honors.
          </CardDescription>
        </div>

        <Button
          size="sm"
          variant={isAdding ? 'outline' : 'default'}
          onClick={() => {
            setIsAdding(!isAdding)
            setErrorMsg(null)
          }}
          data-testid="toggle-add-education-btn"
        >
          {isAdding ? 'Cancel' : (
            <>
              <Plus className="mr-1.5 h-4 w-4" />
              Add Education
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
            data-testid="add-education-form"
          >
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Add Education Record
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label htmlFor="edu-institution" className="text-xs font-medium text-foreground">
                  Institution *
                </label>
                <Input
                  id="edu-institution"
                  placeholder="e.g. Stanford University"
                  value={institution}
                  onChange={(e) => setInstitution(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="edu-degree" className="text-xs font-medium text-foreground">
                  Degree *
                </label>
                <Input
                  id="edu-degree"
                  placeholder="e.g. Bachelor of Technology"
                  value={degree}
                  onChange={(e) => setDegree(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="edu-field" className="text-xs font-medium text-foreground">
                  Field of Study *
                </label>
                <Input
                  id="edu-field"
                  placeholder="e.g. Computer Science"
                  value={fieldOfStudy}
                  onChange={(e) => setFieldOfStudy(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div className="space-y-1">
                <label htmlFor="edu-level" className="text-xs font-medium text-foreground">
                  Education Level
                </label>
                <select
                  id="edu-level"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={educationLevel}
                  onChange={(e) => setEducationLevel(e.target.value as EducationLevel)}
                >
                  <option value="bachelor">Bachelor</option>
                  <option value="master">Master</option>
                  <option value="phd">PhD / Doctorate</option>
                  <option value="diploma">Diploma</option>
                  <option value="none">Certificate / None</option>
                </select>
              </div>

              <div className="space-y-1">
                <label htmlFor="edu-start-date" className="text-xs font-medium text-foreground">
                  Start Date
                </label>
                <Input
                  id="edu-start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="edu-end-date" className="text-xs font-medium text-foreground">
                  End Date
                </label>
                <Input
                  id="edu-end-date"
                  type="date"
                  disabled={isCurrent}
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="edu-grade" className="text-xs font-medium text-foreground">
                  Grade / CGPA
                </label>
                <Input
                  id="edu-grade"
                  placeholder="e.g. 8.9 / 10 or 3.8 / 4.0"
                  value={grade}
                  onChange={(e) => setGrade(e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="edu-current"
                checked={isCurrent}
                onChange={(e) => setIsCurrent(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <label htmlFor="edu-current" className="text-xs font-medium text-foreground cursor-pointer">
                Currently pursuing this degree
              </label>
            </div>

            <div className="space-y-1">
              <label htmlFor="edu-description" className="text-xs font-medium text-foreground">
                Description / Honors (Optional)
              </label>
              <Input
                id="edu-description"
                placeholder="Relevant coursework, academic achievements..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
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
                {isSubmitting ? 'Saving...' : 'Save Education'}
              </Button>
            </div>
          </form>
        )}

        {educations.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
            No education records added yet.
          </div>
        ) : (
          <div className="space-y-3" data-testid="education-list">
            {educations.map((edu) => (
              <div
                key={edu.id}
                className="flex items-start justify-between rounded-lg border border-border bg-card p-4 text-xs transition-colors hover:border-primary/40"
                data-testid={`education-item-${edu.id}`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-sm text-foreground">
                      {edu.degree} in {edu.field_of_study}
                    </h4>
                    {edu.education_level && (
                      <Badge variant="outline" className="text-[10px] capitalize">
                        {edu.education_level}
                      </Badge>
                    )}
                  </div>

                  <p className="font-medium text-muted-foreground">{edu.institution}</p>

                  <div className="flex items-center gap-3 text-[11px] text-muted-foreground pt-1">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3 text-primary" />
                      {edu.start_date || 'N/A'} &ndash;{' '}
                      {edu.is_current ? 'Present' : edu.end_date || 'N/A'}
                    </span>
                    {edu.grade && <span>&bull; Grade: {edu.grade}</span>}
                  </div>

                  {edu.description && (
                    <p className="text-muted-foreground pt-1">{edu.description}</p>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => handleDelete(edu.id)}
                  disabled={deletingId === edu.id}
                  className="text-muted-foreground hover:text-red-500 transition-colors p-1 rounded cursor-pointer"
                  title="Remove education"
                  aria-label={`Remove ${edu.degree}`}
                  data-testid={`delete-education-${edu.id}`}
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
