import * as React from 'react'
import {
  AlertCircle,
  CheckCircle2,
  Globe,
  Link as LinkIcon,
  MapPin,
  Phone,
  Save,
  User,
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
import type { ProfileDetailResponse, ProfileUpdate } from '@/types/profile'

interface BasicInfoSectionProps {
  profile: ProfileDetailResponse
  isEditing: boolean
  onUpdate: (payload: ProfileUpdate) => Promise<void>
}

export function BasicInfoSection({
  profile,
  isEditing,
  onUpdate,
}: BasicInfoSectionProps) {
  const [fullName, setFullName] = React.useState(profile.full_name || '')
  const [headline, setHeadline] = React.useState(profile.headline || '')
  const [summary, setSummary] = React.useState(profile.summary || '')
  const [phone, setPhone] = React.useState(profile.phone || '')
  const [city, setCity] = React.useState(profile.location_city || '')
  const [state, setState] = React.useState(profile.location_state || '')
  const [country, setCountry] = React.useState(profile.location_country || '')
  const [linkedinUrl, setLinkedinUrl] = React.useState(profile.linkedin_url || '')
  const [githubUrl, setGithubUrl] = React.useState(profile.github_url || '')
  const [portfolioUrl, setPortfolioUrl] = React.useState(profile.portfolio_url || '')

  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [formError, setFormError] = React.useState<string | null>(null)
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    setSuccessMsg(null)

    if (!fullName.trim()) {
      setFormError('Full name is required.')
      return
    }

    try {
      setIsSubmitting(true)
      await onUpdate({
        full_name: fullName.trim(),
        headline: headline.trim() || null,
        summary: summary.trim() || null,
        phone: phone.trim() || null,
        location_city: city.trim() || null,
        location_state: state.trim() || null,
        location_country: country.trim() || null,
        linkedin_url: linkedinUrl.trim() || null,
        github_url: githubUrl.trim() || null,
        portfolio_url: portfolioUrl.trim() || null,
      })
      setSuccessMsg('Basic information saved successfully!')
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to update profile.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <User className="h-5 w-5 text-primary" aria-hidden="true" />
          Basic Information
        </CardTitle>
        <CardDescription>
          Personal details, professional headline, summary, and contact links.
        </CardDescription>
      </CardHeader>

      <CardContent>
        {isEditing ? (
          <form onSubmit={handleSubmit} className="space-y-4" data-testid="basic-info-form">
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
                <label htmlFor="info-full-name" className="text-xs font-semibold text-foreground">
                  Full Name *
                </label>
                <Input
                  id="info-full-name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Jordan Lee"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="info-headline" className="text-xs font-semibold text-foreground">
                  Professional Headline
                </label>
                <Input
                  id="info-headline"
                  value={headline}
                  onChange={(e) => setHeadline(e.target.value)}
                  placeholder="e.g. Senior Backend Engineer"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="info-summary" className="text-xs font-semibold text-foreground">
                Professional Summary
              </label>
              <textarea
                id="info-summary"
                rows={3}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="Brief summary of your professional background and career trajectory..."
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-1.5">
                <label htmlFor="info-phone" className="text-xs font-semibold text-foreground">
                  Phone
                </label>
                <Input
                  id="info-phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+91 9876543210"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="info-city" className="text-xs font-semibold text-foreground">
                  City
                </label>
                <Input
                  id="info-city"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="Bengaluru"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="info-state" className="text-xs font-semibold text-foreground">
                  State
                </label>
                <Input
                  id="info-state"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  placeholder="Karnataka"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="info-country" className="text-xs font-semibold text-foreground">
                  Country
                </label>
                <Input
                  id="info-country"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  placeholder="India"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label htmlFor="info-linkedin" className="text-xs font-semibold text-foreground">
                  LinkedIn URL
                </label>
                <Input
                  id="info-linkedin"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  placeholder="https://linkedin.com/in/..."
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="info-github" className="text-xs font-semibold text-foreground">
                  GitHub URL
                </label>
                <Input
                  id="info-github"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/..."
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="info-portfolio" className="text-xs font-semibold text-foreground">
                  Portfolio URL
                </label>
                <Input
                  id="info-portfolio"
                  value={portfolioUrl}
                  onChange={(e) => setPortfolioUrl(e.target.value)}
                  placeholder="https://myportfolio.dev"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={isSubmitting} size="sm">
                <Save className="mr-1.5 h-4 w-4" />
                {isSubmitting ? 'Saving...' : 'Save Basic Info'}
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-4 text-sm" data-testid="basic-info-display">
            {profile.summary && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                  Summary
                </h3>
                <p className="text-muted-foreground whitespace-pre-line leading-relaxed">
                  {profile.summary}
                </p>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-2 border-t border-border">
              {profile.phone && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Phone className="h-4 w-4 text-primary shrink-0" />
                  <span>{profile.phone}</span>
                </div>
              )}

              {(profile.location_city || profile.location_state || profile.location_country) && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <MapPin className="h-4 w-4 text-primary shrink-0" />
                  <span>
                    {[profile.location_city, profile.location_state, profile.location_country]
                      .filter(Boolean)
                      .join(', ')}
                  </span>
                </div>
              )}

              {profile.linkedin_url && (
                <a
                  href={profile.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-xs text-primary hover:underline"
                >
                  <LinkIcon className="h-4 w-4 shrink-0" />
                  <span className="truncate">LinkedIn Profile</span>
                </a>
              )}

              {profile.github_url && (
                <a
                  href={profile.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-xs text-primary hover:underline"
                >
                  <LinkIcon className="h-4 w-4 shrink-0" />
                  <span className="truncate">GitHub Profile</span>
                </a>
              )}

              {profile.portfolio_url && (
                <a
                  href={profile.portfolio_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-xs text-primary hover:underline"
                >
                  <Globe className="h-4 w-4 shrink-0" />
                  <span className="truncate">Portfolio Website</span>
                </a>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
