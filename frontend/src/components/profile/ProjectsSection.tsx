import * as React from 'react'
import {
  AlertCircle,
  Calendar,
  Code2,
  ExternalLink,
  FolderGit2,
  Plus,
  Trash2,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { ProjectCreate, ProjectResponse } from '@/types/profile'

interface ProjectsSectionProps {
  projects: ProjectResponse[]
  onAddProject: (payload: ProjectCreate) => Promise<void>
  onDeleteProject: (projectId: string) => Promise<void>
}

function isValidUrl(val: string): boolean {
  if (!val) return true
  try {
    const url = new URL(val)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

export function ProjectsSection({
  projects,
  onAddProject,
  onDeleteProject,
}: ProjectsSectionProps) {
  const [isAdding, setIsAdding] = React.useState(false)
  const [title, setTitle] = React.useState('')
  const [description, setDescription] = React.useState('')
  const [techInput, setTechInput] = React.useState('')
  const [projectUrl, setProjectUrl] = React.useState('')
  const [repoUrl, setRepoUrl] = React.useState('')
  const [startDate, setStartDate] = React.useState('')
  const [endDate, setEndDate] = React.useState('')

  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null)
  const [deletingId, setDeletingId] = React.useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)

    if (!title.trim()) {
      setErrorMsg('Project title is required.')
      return
    }

    if (projectUrl.trim() && !isValidUrl(projectUrl.trim())) {
      setErrorMsg('Live Demo URL must be a valid HTTP/HTTPS URL.')
      return
    }

    if (repoUrl.trim() && !isValidUrl(repoUrl.trim())) {
      setErrorMsg('Repository URL must be a valid HTTP/HTTPS URL.')
      return
    }

    if (startDate && endDate && endDate < startDate) {
      setErrorMsg('End date cannot be earlier than start date.')
      return
    }

    const technologies = techInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)

    try {
      setIsSubmitting(true)
      await onAddProject({
        title: title.trim(),
        description: description.trim() || null,
        technologies,
        project_url: projectUrl.trim() || null,
        repo_url: repoUrl.trim() || null,
        start_date: startDate || null,
        end_date: endDate || null,
      })
      // Reset form
      setTitle('')
      setDescription('')
      setTechInput('')
      setProjectUrl('')
      setRepoUrl('')
      setStartDate('')
      setEndDate('')
      setIsAdding(false)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to add project.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      setDeletingId(id)
      await onDeleteProject(id)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to delete project.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle className="text-lg flex items-center gap-2">
            <FolderGit2 className="h-5 w-5 text-primary" aria-hidden="true" />
            Projects ({projects.length})
          </CardTitle>
          <CardDescription>
            Portfolio artifacts, open-source work, and technical projects.
          </CardDescription>
        </div>

        <Button
          size="sm"
          variant={isAdding ? 'outline' : 'default'}
          onClick={() => {
            setIsAdding(!isAdding)
            setErrorMsg(null)
          }}
          data-testid="toggle-add-project-btn"
        >
          {isAdding ? 'Cancel' : (
            <>
              <Plus className="mr-1.5 h-4 w-4" />
              Add Project
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
            data-testid="add-project-form"
          >
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Add New Project
            </h4>

            <div className="space-y-1">
              <label htmlFor="proj-title" className="text-xs font-medium text-foreground">
                Project Title *
              </label>
              <Input
                id="proj-title"
                placeholder="e.g. Distributed Consensus Engine"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1">
              <label htmlFor="proj-desc" className="text-xs font-medium text-foreground">
                Project Description
              </label>
              <textarea
                id="proj-desc"
                rows={3}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="High-performance Raft consensus implementation in Go with gRPC transport..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label htmlFor="proj-tech" className="text-xs font-medium text-foreground">
                Technologies Used (comma-separated)
              </label>
              <Input
                id="proj-tech"
                placeholder="Go, Raft, gRPC, Docker"
                value={techInput}
                onChange={(e) => setTechInput(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="proj-demo-url" className="text-xs font-medium text-foreground">
                  Live Project URL
                </label>
                <Input
                  id="proj-demo-url"
                  placeholder="https://myproject.demo.dev"
                  value={projectUrl}
                  onChange={(e) => setProjectUrl(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="proj-repo-url" className="text-xs font-medium text-foreground">
                  Source Code / Repo URL
                </label>
                <Input
                  id="proj-repo-url"
                  placeholder="https://github.com/myusername/project"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="proj-start-date" className="text-xs font-medium text-foreground">
                  Start Date
                </label>
                <Input
                  id="proj-start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="proj-end-date" className="text-xs font-medium text-foreground">
                  End Date
                </label>
                <Input
                  id="proj-end-date"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
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
                {isSubmitting ? 'Saving...' : 'Save Project'}
              </Button>
            </div>
          </form>
        )}

        {projects.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
            No projects added yet.
          </div>
        ) : (
          <div className="space-y-3" data-testid="project-list">
            {projects.map((proj) => (
              <div
                key={proj.id}
                className="flex items-start justify-between rounded-lg border border-border bg-card p-4 text-xs transition-colors hover:border-primary/40"
                data-testid={`project-item-${proj.id}`}
              >
                <div className="space-y-1.5">
                  <h4 className="font-semibold text-sm text-foreground">
                    {proj.title}
                  </h4>

                  {(proj.start_date || proj.end_date) && (
                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <Calendar className="h-3 w-3 text-primary" />
                      <span>
                        {proj.start_date || 'N/A'} &ndash; {proj.end_date || 'Present'}
                      </span>
                    </div>
                  )}

                  {proj.description && (
                    <p className="text-muted-foreground pt-1 leading-relaxed whitespace-pre-line">
                      {proj.description}
                    </p>
                  )}

                  {proj.technologies && proj.technologies.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {proj.technologies.map((tech) => (
                        <span
                          key={tech}
                          className="rounded-md bg-muted px-2 py-0.5 text-[10px] font-medium text-foreground"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="flex flex-wrap items-center gap-3 pt-2">
                    {proj.project_url && (
                      <a
                        href={proj.project_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-primary hover:underline text-[11px]"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Live Demo
                      </a>
                    )}
                    {proj.repo_url && (
                      <a
                        href={proj.repo_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-primary hover:underline text-[11px]"
                      >
                        <Code2 className="h-3 w-3" />
                        Source Code
                      </a>
                    )}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleDelete(proj.id)}
                  disabled={deletingId === proj.id}
                  className="text-muted-foreground hover:text-red-500 transition-colors p-1 rounded cursor-pointer"
                  title="Remove project"
                  aria-label={`Remove ${proj.title}`}
                  data-testid={`delete-project-${proj.id}`}
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
