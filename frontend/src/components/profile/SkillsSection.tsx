import * as React from 'react'
import {
  AlertCircle,
  Code2,
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
  SkillCategory,
  SkillCreate,
  SkillProficiency,
  SkillResponse,
} from '@/types/profile'

interface SkillsSectionProps {
  skills: SkillResponse[]
  onAddSkill: (payload: SkillCreate) => Promise<void>
  onDeleteSkill: (skillId: string) => Promise<void>
}

export function SkillsSection({
  skills,
  onAddSkill,
  onDeleteSkill,
}: SkillsSectionProps) {
  const [isAdding, setIsAdding] = React.useState(false)
  const [skillName, setSkillName] = React.useState('')
  const [category, setCategory] = React.useState<SkillCategory>('technical')
  const [proficiency, setProficiency] = React.useState<SkillProficiency>('intermediate')
  const [years, setYears] = React.useState('')
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null)
  const [deletingId, setDeletingId] = React.useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)

    if (!skillName.trim()) {
      setErrorMsg('Skill name is required.')
      return
    }

    const yearsNum = years ? parseInt(years, 10) : null
    if (yearsNum !== null && (yearsNum < 0 || yearsNum > 70)) {
      setErrorMsg('Years of experience must be between 0 and 70.')
      return
    }

    try {
      setIsSubmitting(true)
      await onAddSkill({
        skill_name: skillName.trim(),
        category,
        proficiency_level: proficiency,
        years_of_experience: yearsNum,
        source: 'manual',
      })
      setSkillName('')
      setYears('')
      setIsAdding(false)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to add skill.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      setDeletingId(id)
      await onDeleteSkill(id)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to delete skill.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle className="text-lg flex items-center gap-2">
            <Code2 className="h-5 w-5 text-primary" aria-hidden="true" />
            Skills & Competencies ({skills.length})
          </CardTitle>
          <CardDescription>
            Technical expertise, frameworks, tools, and domain proficiencies.
          </CardDescription>
        </div>

        <Button
          size="sm"
          variant={isAdding ? 'outline' : 'default'}
          onClick={() => {
            setIsAdding(!isAdding)
            setErrorMsg(null)
          }}
          data-testid="toggle-add-skill-btn"
        >
          {isAdding ? 'Cancel' : (
            <>
              <Plus className="mr-1.5 h-4 w-4" />
              Add Skill
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
            data-testid="add-skill-form"
          >
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Add New Skill
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div className="space-y-1">
                <label htmlFor="skill-name-input" className="text-xs font-medium text-foreground">
                  Skill Name *
                </label>
                <Input
                  id="skill-name-input"
                  placeholder="e.g. Python, Docker"
                  value={skillName}
                  onChange={(e) => setSkillName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="skill-category-select" className="text-xs font-medium text-foreground">
                  Category
                </label>
                <select
                  id="skill-category-select"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={category}
                  onChange={(e) => setCategory(e.target.value as SkillCategory)}
                >
                  <option value="technical">Technical</option>
                  <option value="tool">Tool</option>
                  <option value="soft">Soft</option>
                  <option value="language">Language</option>
                  <option value="domain">Domain</option>
                </select>
              </div>

              <div className="space-y-1">
                <label htmlFor="skill-proficiency-select" className="text-xs font-medium text-foreground">
                  Proficiency
                </label>
                <select
                  id="skill-proficiency-select"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={proficiency}
                  onChange={(e) => setProficiency(e.target.value as SkillProficiency)}
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                  <option value="expert">Expert</option>
                </select>
              </div>

              <div className="space-y-1">
                <label htmlFor="skill-years-input" className="text-xs font-medium text-foreground">
                  Years of Exp.
                </label>
                <Input
                  id="skill-years-input"
                  type="number"
                  min="0"
                  max="70"
                  placeholder="e.g. 3"
                  value={years}
                  onChange={(e) => setYears(e.target.value)}
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
                {isSubmitting ? 'Adding...' : 'Save Skill'}
              </Button>
            </div>
          </form>
        )}

        {skills.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
            No skills added yet. Add your skills manually or sync from your parsed resume.
          </div>
        ) : (
          <div className="flex flex-wrap gap-2.5" data-testid="skills-list">
            {skills.map((skill) => (
              <div
                key={skill.id}
                className="group flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs shadow-xs transition-colors hover:border-primary/40"
                data-testid={`skill-badge-${skill.id}`}
              >
                <span className="font-semibold text-foreground">{skill.skill_name}</span>
                {skill.category && (
                  <Badge variant="secondary" className="text-[10px] uppercase px-1.5 py-0">
                    {skill.category}
                  </Badge>
                )}
                {skill.proficiency_level && (
                  <span className="text-muted-foreground capitalize text-[11px]">
                    &bull; {skill.proficiency_level}
                  </span>
                )}
                {skill.years_of_experience !== null && skill.years_of_experience !== undefined && (
                  <span className="text-muted-foreground text-[11px]">
                    ({skill.years_of_experience}y)
                  </span>
                )}
                {skill.source === 'resume' && (
                  <Badge variant="outline" className="text-[9px] px-1 py-0 text-muted-foreground">
                    resume
                  </Badge>
                )}
                <button
                  type="button"
                  onClick={() => handleDelete(skill.id)}
                  disabled={deletingId === skill.id}
                  className="text-muted-foreground hover:text-red-500 transition-colors p-0.5 rounded cursor-pointer"
                  title="Remove skill"
                  aria-label={`Remove ${skill.skill_name}`}
                  data-testid={`delete-skill-${skill.id}`}
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
