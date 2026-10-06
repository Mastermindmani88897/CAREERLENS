import {
  Briefcase,
  CheckCircle2,
  Globe,
  MapPin,
  User,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { ProfileDetailResponse } from '@/types/profile'

interface ProfileHeaderProps {
  profile: ProfileDetailResponse
  isEditing: boolean
  onToggleEdit: () => void
}

export function ProfileHeader({
  profile,
  isEditing,
  onToggleEdit,
}: ProfileHeaderProps) {
  const locationParts = [
    profile.location_city,
    profile.location_state,
    profile.location_country,
  ].filter(Boolean)

  const locationText = locationParts.join(', ') || 'Location not specified'

  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary border border-primary/20 shadow-sm">
            <User className="h-8 w-8" aria-hidden="true" />
          </div>

          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-foreground">
                {profile.full_name || 'Candidate Profile'}
              </h1>
              {profile.open_to_relocation && (
                <Badge variant="outline" className="text-xs text-emerald-600 dark:text-emerald-400 border-emerald-500/30">
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                  Open to Relocation
                </Badge>
              )}
            </div>

            <p className="text-sm font-medium text-muted-foreground">
              {profile.headline || 'No headline set'}
            </p>

            <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground pt-1">
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                {locationText}
              </span>
              <span className="flex items-center gap-1">
                <Briefcase className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                {profile.preferred_work_mode ? `Mode: ${profile.preferred_work_mode}` : 'Work mode flexible'}
              </span>
              {profile.portfolio_url && (
                <a
                  href={profile.portfolio_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-primary hover:underline"
                >
                  <Globe className="h-3.5 w-3.5" aria-hidden="true" />
                  Portfolio
                </a>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <Button
            variant={isEditing ? 'outline' : 'default'}
            onClick={onToggleEdit}
            className="w-full md:w-auto"
            data-testid="toggle-edit-btn"
          >
            {isEditing ? 'Cancel Edit' : 'Edit Profile'}
          </Button>
        </div>
      </div>
    </div>
  )
}
