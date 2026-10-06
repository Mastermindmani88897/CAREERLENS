import * as React from 'react'
import {
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  ShieldCheck,
  Sparkles,
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
import type { ProfileSyncResult } from '@/types/profile'

interface ResumeSyncSectionProps {
  onSync: (resumeId: string) => Promise<ProfileSyncResult>
}

export function ResumeSyncSection({ onSync }: ResumeSyncSectionProps) {
  const [resumeId, setResumeId] = React.useState('')
  const [isSyncing, setIsSyncing] = React.useState(false)
  const [syncResult, setSyncResult] = React.useState<ProfileSyncResult | null>(null)
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null)

  const handleSyncSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)

    if (!resumeId.trim()) {
      setErrorMsg('Please enter a valid Resume Document ID to synchronize.')
      return
    }

    try {
      setIsSyncing(true)
      const res = await onSync(resumeId.trim())
      setSyncResult(res)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Resume synchronization failed.')
    } finally {
      setIsSyncing(false)
    }
  }

  return (
    <Card className="border-primary/20 shadow-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-primary" aria-hidden="true" />
            Resume-to-Profile Synchronization
          </CardTitle>
          <Badge variant="outline" className="text-xs font-medium text-primary border-primary/30">
            Phase 12 Pipeline
          </Badge>
        </div>
        <CardDescription>
          Deterministically import extracted skills, education, and career history from an uploaded resume.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Guarantees Box */}
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3 text-xs text-muted-foreground space-y-1.5">
          <div className="flex items-center gap-1.5 font-semibold text-foreground">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <span>Preservation & Non-Destructive Merge Guarantee</span>
          </div>
          <p>
            Existing user-customized fields (such as your headline, summary, and preferred locations)
            and all manually added items are <strong>never overwritten or deleted</strong>. Synchronization is idempotent and duplicate-free.
          </p>
        </div>

        {errorMsg && (
          <div
            role="alert"
            className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-600 dark:text-red-400"
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSyncSubmit} className="space-y-3" data-testid="resume-sync-form">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 space-y-1">
              <label htmlFor="sync-resume-id" className="text-xs font-semibold text-foreground">
                Parsed Resume Document ID
              </label>
              <Input
                id="sync-resume-id"
                placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
                value={resumeId}
                onChange={(e) => setResumeId(e.target.value)}
                required
              />
            </div>
            <div className="sm:self-end">
              <Button type="submit" disabled={isSyncing} className="w-full sm:w-auto" data-testid="sync-resume-btn">
                <Sparkles className="mr-2 h-4 w-4" />
                {isSyncing ? 'Synchronizing...' : 'Sync Resume to Profile'}
              </Button>
            </div>
          </div>
        </form>

        {syncResult && (
          <div
            className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 space-y-3 animate-in fade-in duration-300"
            data-testid="sync-result-card"
          >
            <div className="flex items-center gap-2 text-sm font-bold text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="h-5 w-5 shrink-0" />
              <span>{syncResult.message}</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center pt-2">
              <div className="rounded-lg bg-card border border-border p-2">
                <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                  Skills Added
                </span>
                <span className="text-base font-bold text-foreground">
                  +{syncResult.skills_added}
                </span>
              </div>

              <div className="rounded-lg bg-card border border-border p-2">
                <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                  Education Added
                </span>
                <span className="text-base font-bold text-foreground">
                  +{syncResult.educations_added}
                </span>
              </div>

              <div className="rounded-lg bg-card border border-border p-2">
                <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                  Experience Added
                </span>
                <span className="text-base font-bold text-foreground">
                  +{syncResult.experiences_added}
                </span>
              </div>

              <div className="rounded-lg bg-card border border-border p-2">
                <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                  Projects Added
                </span>
                <span className="text-base font-bold text-foreground">
                  +{syncResult.projects_added}
                </span>
              </div>

              <div className="rounded-lg bg-card border border-border p-2 col-span-2 sm:col-span-1">
                <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                  Certs Added
                </span>
                <span className="text-base font-bold text-foreground">
                  +{syncResult.certifications_added}
                </span>
              </div>
            </div>

            {syncResult.fields_updated && syncResult.fields_updated.length > 0 && (
              <div className="text-xs pt-1 text-muted-foreground">
                <span className="font-semibold text-foreground">Root fields populated: </span>
                {syncResult.fields_updated.join(', ')}
              </div>
            )}

            {syncResult.preserved_fields && syncResult.preserved_fields.length > 0 && (
              <div className="text-xs pt-0.5 text-muted-foreground">
                <span className="font-semibold text-foreground">Protected user fields preserved: </span>
                {syncResult.preserved_fields.join(', ')}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
