import * as React from 'react'
import {
  AlertCircle,
  CheckCircle2,
  Save,
  Sliders,
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
import type {
  EmploymentType,
  ProfileDetailResponse,
  ProfileUpdate,
  WorkMode,
} from '@/types/profile'

interface PreferencesSectionProps {
  profile: ProfileDetailResponse
  isEditing: boolean
  onUpdate: (payload: ProfileUpdate) => Promise<void>
}

export function PreferencesSection({
  profile,
  isEditing,
  onUpdate,
}: PreferencesSectionProps) {
  const [workMode, setWorkMode] = React.useState<WorkMode>(profile.preferred_work_mode || 'any')
  const [employmentType, setEmploymentType] = React.useState<EmploymentType>(
    profile.preferred_employment_type || 'any'
  )
  const [salaryMin, setSalaryMin] = React.useState<string>(
    profile.preferred_salary_min !== null && profile.preferred_salary_min !== undefined
      ? String(profile.preferred_salary_min)
      : ''
  )
  const [salaryMax, setSalaryMax] = React.useState<string>(
    profile.preferred_salary_max !== null && profile.preferred_salary_max !== undefined
      ? String(profile.preferred_salary_max)
      : ''
  )
  const [currency, setCurrency] = React.useState(profile.preferred_salary_currency || 'INR')
  const [openToRelocation, setOpenToRelocation] = React.useState(Boolean(profile.open_to_relocation))

  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [formError, setFormError] = React.useState<string | null>(null)
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    setSuccessMsg(null)

    const minNum = salaryMin ? parseInt(salaryMin, 10) : null
    const maxNum = salaryMax ? parseInt(salaryMax, 10) : null

    if (minNum !== null && minNum < 0) {
      setFormError('Minimum salary cannot be negative.')
      return
    }
    if (maxNum !== null && maxNum < 0) {
      setFormError('Maximum salary cannot be negative.')
      return
    }
    if (minNum !== null && maxNum !== null && minNum > maxNum) {
      setFormError('Minimum salary cannot be greater than maximum salary.')
      return
    }

    try {
      setIsSubmitting(true)
      await onUpdate({
        preferred_work_mode: workMode,
        preferred_employment_type: employmentType,
        preferred_salary_min: minNum,
        preferred_salary_max: maxNum,
        preferred_salary_currency: currency.trim() || 'INR',
        open_to_relocation: openToRelocation,
      })
      setSuccessMsg('Career preferences saved successfully!')
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to save preferences.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Sliders className="h-5 w-5 text-primary" aria-hidden="true" />
          Career Preferences
        </CardTitle>
        <CardDescription>
          Work flexibility, employment nature, target compensation, and relocation readiness.
        </CardDescription>
      </CardHeader>

      <CardContent>
        {isEditing ? (
          <form onSubmit={handleSubmit} className="space-y-4" data-testid="preferences-form">
            {formError && (
              <div
                role="alert"
                className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-600 dark:text-red-400"
              >
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}
            {successMsg && (
              <div
                role="status"
                className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-600 dark:text-emerald-400"
              >
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label htmlFor="pref-work-mode" className="text-xs font-semibold text-foreground">
                  Preferred Work Mode
                </label>
                <select
                  id="pref-work-mode"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={workMode}
                  onChange={(e) => setWorkMode(e.target.value as WorkMode)}
                >
                  <option value="any">Any (Flexible)</option>
                  <option value="remote">Remote</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="onsite">Onsite</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="pref-employment-type" className="text-xs font-semibold text-foreground">
                  Preferred Employment Type
                </label>
                <select
                  id="pref-employment-type"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  value={employmentType}
                  onChange={(e) => setEmploymentType(e.target.value as EmploymentType)}
                >
                  <option value="any">Any (Flexible)</option>
                  <option value="fulltime">Full-time</option>
                  <option value="parttime">Part-time</option>
                  <option value="internship">Internship</option>
                  <option value="contract">Contract</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label htmlFor="pref-salary-min" className="text-xs font-semibold text-foreground">
                  Minimum Salary
                </label>
                <Input
                  id="pref-salary-min"
                  type="number"
                  min="0"
                  value={salaryMin}
                  onChange={(e) => setSalaryMin(e.target.value)}
                  placeholder="e.g. 600000"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="pref-salary-max" className="text-xs font-semibold text-foreground">
                  Maximum Expected Salary
                </label>
                <Input
                  id="pref-salary-max"
                  type="number"
                  min="0"
                  value={salaryMax}
                  onChange={(e) => setSalaryMax(e.target.value)}
                  placeholder="e.g. 1200000"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="pref-salary-currency" className="text-xs font-semibold text-foreground">
                  Currency
                </label>
                <Input
                  id="pref-salary-currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  placeholder="INR, USD, EUR..."
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <input
                type="checkbox"
                id="pref-relocation"
                checked={openToRelocation}
                onChange={(e) => setOpenToRelocation(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <label htmlFor="pref-relocation" className="text-xs font-medium text-foreground cursor-pointer">
                Open to relocation for suitable career opportunities
              </label>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={isSubmitting} size="sm">
                <Save className="mr-1.5 h-4 w-4" />
                {isSubmitting ? 'Saving...' : 'Save Preferences'}
              </Button>
            </div>
          </form>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs" data-testid="preferences-display">
            <div className="rounded-lg border border-border p-3 space-y-1 bg-muted/20">
              <span className="text-muted-foreground uppercase tracking-wider font-semibold">Work Mode</span>
              <p className="font-medium text-sm text-foreground capitalize">
                {profile.preferred_work_mode || 'Any'}
              </p>
            </div>

            <div className="rounded-lg border border-border p-3 space-y-1 bg-muted/20">
              <span className="text-muted-foreground uppercase tracking-wider font-semibold">Employment</span>
              <p className="font-medium text-sm text-foreground capitalize">
                {profile.preferred_employment_type || 'Any'}
              </p>
            </div>

            <div className="rounded-lg border border-border p-3 space-y-1 bg-muted/20">
              <span className="text-muted-foreground uppercase tracking-wider font-semibold">Target Compensation</span>
              <p className="font-medium text-sm text-foreground">
                {profile.preferred_salary_min || profile.preferred_salary_max ? (
                  `${profile.preferred_salary_currency || 'INR'} ${
                    profile.preferred_salary_min?.toLocaleString() || '0'
                  } – ${profile.preferred_salary_max?.toLocaleString() || 'Flexible'}`
                ) : (
                  'Negotiable'
                )}
              </p>
            </div>

            <div className="rounded-lg border border-border p-3 space-y-1 bg-muted/20">
              <span className="text-muted-foreground uppercase tracking-wider font-semibold">Relocation</span>
              <p className="font-medium text-sm text-foreground">
                {profile.open_to_relocation ? 'Willing to relocate' : 'No relocation'}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
