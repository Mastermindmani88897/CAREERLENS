import React, { useState } from 'react'
import { AlertCircle, CheckCircle2, Loader2, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  APPLICATION_STATUS_LABELS,
  PERMITTED_TRANSITIONS,
  type ApplicationResponse,
  type ApplicationStatus,
} from '@/types/application'
import { ApplicationStatusBadge } from './ApplicationStatusBadge'

interface StatusTransitionModalProps {
  application: ApplicationResponse
  isOpen: boolean
  onClose: () => void
  onTransitionSuccess: (updatedApplication: ApplicationResponse) => void
  onUpdateStatus: (
    applicationId: string,
    targetStatus: ApplicationStatus,
    notes?: string
  ) => Promise<ApplicationResponse>
}

export function StatusTransitionModal({
  application,
  isOpen,
  onClose,
  onTransitionSuccess,
  onUpdateStatus,
}: StatusTransitionModalProps) {
  const currentStatus = application.status
  const permittedTargets = PERMITTED_TRANSITIONS[currentStatus] || []
  const isTerminal = permittedTargets.length === 0

  const [selectedStatus, setSelectedStatus] = useState<ApplicationStatus | ''>(
    permittedTargets.length > 0 ? permittedTargets[0] : ''
  )
  const [notes, setNotes] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedStatus || isTerminal) return

    setIsLoading(true)
    setErrorMessage(null)

    try {
      const updated = await onUpdateStatus(
        application.id,
        selectedStatus as ApplicationStatus,
        notes.trim() || undefined
      )
      onTransitionSuccess(updated)
      onClose()
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message)
      } else {
        setErrorMessage('Failed to update application status.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="transition-modal-title"
    >
      <div
        className="w-full max-w-lg bg-background rounded-xl border border-border shadow-2xl overflow-hidden p-6 space-y-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between pb-3 border-b border-border">
          <div>
            <h2
              id="transition-modal-title"
              className="text-lg font-bold text-foreground"
            >
              Update Application Status
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {application.opportunity?.title ?? 'Opportunity'} &bull;{' '}
              {application.opportunity?.company ?? 'Company'}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="text-muted-foreground hover:text-foreground p-1 rounded-md transition-colors"
            aria-label="Close dialog"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Current Status Banner */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border border-border/80">
          <span className="text-xs font-medium text-muted-foreground">
            Current Status
          </span>
          <ApplicationStatusBadge status={currentStatus} />
        </div>

        {errorMessage && (
          <div
            className="flex items-start gap-2 p-3 text-xs rounded-lg bg-destructive/10 text-destructive border border-destructive/20"
            role="alert"
          >
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
            <span>{errorMessage}</span>
          </div>
        )}

        {isTerminal ? (
          <div className="p-4 rounded-lg bg-muted text-center space-y-2">
            <p className="text-sm font-semibold text-foreground">
              Terminal Lifecycle State
            </p>
            <p className="text-xs text-muted-foreground">
              This application has reached a terminal state ({APPLICATION_STATUS_LABELS[currentStatus]}).
              Further status transitions are not permitted.
            </p>
            <div className="pt-2">
              <Button variant="outline" size="sm" onClick={onClose}>
                Close
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="target-status-select"
                className="block text-xs font-semibold text-foreground uppercase tracking-wider mb-2"
              >
                Permitted Next Status
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2" role="radiogroup" aria-label="Permitted status transitions">
                {permittedTargets.map((statusKey) => {
                  const isSelected = selectedStatus === statusKey
                  return (
                    <button
                      key={statusKey}
                      type="button"
                      role="radio"
                      aria-checked={isSelected}
                      onClick={() => setSelectedStatus(statusKey)}
                      disabled={isLoading}
                      className={`flex items-center justify-between p-3 rounded-lg border text-left text-xs transition-all ${
                        isSelected
                          ? 'border-primary bg-primary/10 text-primary font-semibold ring-1 ring-primary'
                          : 'border-border bg-card hover:bg-muted/50 text-foreground'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <ApplicationStatusBadge status={statusKey} showIcon={false} />
                      </div>
                      {isSelected && (
                        <CheckCircle2 className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            <div>
              <label
                htmlFor="transition-notes"
                className="block text-xs font-semibold text-foreground uppercase tracking-wider mb-1"
              >
                Transition Notes <span className="text-muted-foreground font-normal">(Optional)</span>
              </label>
              <textarea
                id="transition-notes"
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={isLoading}
                placeholder="e.g., Completed second technical round, awaiting feedback."
                className="w-full text-xs rounded-md border border-input bg-background p-2.5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring resize-none"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onClose}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isLoading || !selectedStatus}
                className="min-w-[110px]"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                    Updating...
                  </>
                ) : (
                  'Confirm Update'
                )}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
