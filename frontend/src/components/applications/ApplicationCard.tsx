import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Building2,
  Calendar,
  ExternalLink,
  History,
  MapPin,
  RefreshCw,
  Trash2,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import type { ApplicationResponse, ApplicationStatus } from '@/types/application'
import { ApplicationStatusBadge } from './ApplicationStatusBadge'
import { StatusTransitionModal } from './StatusTransitionModal'

interface ApplicationCardProps {
  application: ApplicationResponse
  onUpdateStatus: (
    applicationId: string,
    targetStatus: ApplicationStatus,
    notes?: string
  ) => Promise<ApplicationResponse>
  onDeleteApplication?: (applicationId: string) => Promise<void>
  onRefresh?: () => void
}

export function ApplicationCard({
  application,
  onUpdateStatus,
  onDeleteApplication,
  onRefresh,
}: ApplicationCardProps) {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  const opp = application.opportunity

  const locationText = [opp?.location_city, opp?.location_state, opp?.location_country]
    .filter(Boolean)
    .join(', ') || 'Location Unspecified'

  const formattedAppliedDate = application.applied_date
    ? new Date(application.applied_date).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : null

  const handleDelete = async () => {
    if (!onDeleteApplication) return
    const confirmed = window.confirm(
      `Are you sure you want to remove the tracked application for "${opp?.title ?? 'this role'}"?`
    )
    if (!confirmed) return

    setIsDeleting(true)
    try {
      await onDeleteApplication(application.id)
      if (onRefresh) onRefresh()
    } catch {
      // Error handled by parent or alert
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <>
      <Card className="hover:border-primary/40 transition-all shadow-xs">
        <CardContent className="p-5 space-y-4">
          {/* Header Row */}
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <Link
                  to={`/opportunities/${application.opportunity_id}`}
                  className="text-base font-bold text-foreground hover:text-primary transition-colors flex items-center gap-1.5"
                >
                  <span>{opp?.title ?? 'Opportunity'}</span>
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                </Link>
                {opp?.is_active === false && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-medium">
                    Inactive
                  </span>
                )}
              </div>

              <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                <span className="flex items-center gap-1 font-medium text-foreground">
                  <Building2 className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                  {opp?.company ?? 'Company'}
                </span>
                <span className="flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                  {locationText}
                </span>
                {opp?.work_mode && (
                  <span className="capitalize px-1.5 py-0.5 rounded bg-muted/60 text-muted-foreground text-[10px]">
                    {opp.work_mode.replace('_', ' ')}
                  </span>
                )}
                {opp?.employment_type && (
                  <span className="capitalize px-1.5 py-0.5 rounded bg-muted/60 text-muted-foreground text-[10px]">
                    {opp.employment_type.replace('_', ' ')}
                  </span>
                )}
              </div>
            </div>

            {/* Current Status Badge */}
            <div className="flex items-center gap-2 self-start shrink-0">
              <ApplicationStatusBadge status={application.status} />
            </div>
          </div>

          {/* Notes and Dates */}
          <div className="pt-2 border-t border-border/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-4 text-muted-foreground flex-wrap">
              {formattedAppliedDate && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                  Applied: {formattedAppliedDate}
                </span>
              )}
              {application.status_history && application.status_history.length > 1 && (
                <button
                  type="button"
                  onClick={() => setShowHistory(!showHistory)}
                  className="flex items-center gap-1 text-primary hover:underline font-medium cursor-pointer"
                >
                  <History className="h-3.5 w-3.5" aria-hidden="true" />
                  {application.status_history.length} status events
                </button>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2 self-end sm:self-auto">
              {onDeleteApplication && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleDelete}
                  disabled={isDeleting}
                  aria-label={`Delete application for ${opp?.title ?? 'opportunity'}`}
                  className="h-8 px-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsModalOpen(true)}
                className="h-8 text-xs font-semibold"
              >
                <RefreshCw className="mr-1.5 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                Update Status
              </Button>
            </div>
          </div>

          {/* Optional Notes Preview */}
          {application.notes && (
            <div className="p-2.5 rounded-lg bg-muted/40 text-xs text-muted-foreground italic border border-border/40">
              <span className="font-semibold not-italic text-foreground">Note: </span>
              {application.notes}
            </div>
          )}

          {/* History Timeline Accordion */}
          {showHistory && application.status_history && (
            <div className="pt-3 border-t border-border/60 space-y-2">
              <h4 className="text-[11px] font-bold text-foreground uppercase tracking-wider">
                Status History Timeline
              </h4>
              <div className="space-y-1.5">
                {application.status_history.map((event) => (
                  <div
                    key={event.id}
                    className="flex items-center justify-between p-2 rounded bg-muted/30 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <ApplicationStatusBadge status={event.status} showIcon={false} />
                      {event.notes && (
                        <span className="text-muted-foreground text-[11px]">
                          {event.notes}
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground shrink-0">
                      {new Date(event.changed_at).toLocaleString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <StatusTransitionModal
        application={application}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onTransitionSuccess={() => {
          if (onRefresh) onRefresh()
        }}
        onUpdateStatus={onUpdateStatus}
      />
    </>
  )
}
