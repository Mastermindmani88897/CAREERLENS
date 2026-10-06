import * as React from 'react'
import {
  AlertCircle,
  Award,
  Calendar,
  ExternalLink,
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
import type { CertificationCreate, CertificationResponse } from '@/types/profile'

interface CertificationsSectionProps {
  certifications: CertificationResponse[]
  onAddCertification: (payload: CertificationCreate) => Promise<void>
  onDeleteCertification: (certificationId: string) => Promise<void>
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

export function CertificationsSection({
  certifications,
  onAddCertification,
  onDeleteCertification,
}: CertificationsSectionProps) {
  const [isAdding, setIsAdding] = React.useState(false)
  const [name, setName] = React.useState('')
  const [issuer, setIssuer] = React.useState('')
  const [issueDate, setIssueDate] = React.useState('')
  const [expiryDate, setExpiryDate] = React.useState('')
  const [credentialId, setCredentialId] = React.useState('')
  const [credentialUrl, setCredentialUrl] = React.useState('')

  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null)
  const [deletingId, setDeletingId] = React.useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)

    if (!name.trim() || !issuer.trim()) {
      setErrorMsg('Certification Name and Issuing Organization are required.')
      return
    }

    if (credentialUrl.trim() && !isValidUrl(credentialUrl.trim())) {
      setErrorMsg('Credential URL must be a valid HTTP/HTTPS URL.')
      return
    }

    if (issueDate && expiryDate && expiryDate < issueDate) {
      setErrorMsg('Expiry date cannot be earlier than issue date.')
      return
    }

    try {
      setIsSubmitting(true)
      await onAddCertification({
        name: name.trim(),
        issuing_organization: issuer.trim(),
        issue_date: issueDate || null,
        expiry_date: expiryDate || null,
        credential_id: credentialId.trim() || null,
        credential_url: credentialUrl.trim() || null,
      })
      // Reset form
      setName('')
      setIssuer('')
      setIssueDate('')
      setExpiryDate('')
      setCredentialId('')
      setCredentialUrl('')
      setIsAdding(false)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to add certification.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      setDeletingId(id)
      await onDeleteCertification(id)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to delete certification.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle className="text-lg flex items-center gap-2">
            <Award className="h-5 w-5 text-primary" aria-hidden="true" />
            Certifications & Licenses ({certifications.length})
          </CardTitle>
          <CardDescription>
            Verified credentials, professional certifications, and licenses.
          </CardDescription>
        </div>

        <Button
          size="sm"
          variant={isAdding ? 'outline' : 'default'}
          onClick={() => {
            setIsAdding(!isAdding)
            setErrorMsg(null)
          }}
          data-testid="toggle-add-certification-btn"
        >
          {isAdding ? 'Cancel' : (
            <>
              <Plus className="mr-1.5 h-4 w-4" />
              Add Certification
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
            data-testid="add-certification-form"
          >
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Add Professional Certification
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="cert-name" className="text-xs font-medium text-foreground">
                  Certification Name *
                </label>
                <Input
                  id="cert-name"
                  placeholder="e.g. AWS Certified Solutions Architect"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="cert-issuer" className="text-xs font-medium text-foreground">
                  Issuing Organization *
                </label>
                <Input
                  id="cert-issuer"
                  placeholder="e.g. Amazon Web Services"
                  value={issuer}
                  onChange={(e) => setIssuer(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="cert-issue-date" className="text-xs font-medium text-foreground">
                  Issue Date
                </label>
                <Input
                  id="cert-issue-date"
                  type="date"
                  value={issueDate}
                  onChange={(e) => setIssueDate(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="cert-expiry-date" className="text-xs font-medium text-foreground">
                  Expiration Date
                </label>
                <Input
                  id="cert-expiry-date"
                  type="date"
                  value={expiryDate}
                  onChange={(e) => setExpiryDate(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor="cert-cred-id" className="text-xs font-medium text-foreground">
                  Credential ID
                </label>
                <Input
                  id="cert-cred-id"
                  placeholder="e.g. AWS-10293847"
                  value={credentialId}
                  onChange={(e) => setCredentialId(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <label htmlFor="cert-cred-url" className="text-xs font-medium text-foreground">
                  Credential Verification URL
                </label>
                <Input
                  id="cert-cred-url"
                  placeholder="https://aws.amazon.com/verify/..."
                  value={credentialUrl}
                  onChange={(e) => setCredentialUrl(e.target.value)}
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
                {isSubmitting ? 'Saving...' : 'Save Certification'}
              </Button>
            </div>
          </form>
        )}

        {certifications.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
            No certifications added yet.
          </div>
        ) : (
          <div className="space-y-3" data-testid="certification-list">
            {certifications.map((cert) => (
              <div
                key={cert.id}
                className="flex items-start justify-between rounded-lg border border-border bg-card p-4 text-xs transition-colors hover:border-primary/40"
                data-testid={`certification-item-${cert.id}`}
              >
                <div className="space-y-1">
                  <h4 className="font-semibold text-sm text-foreground">
                    {cert.name}
                  </h4>
                  <p className="font-medium text-muted-foreground">
                    {cert.issuing_organization}
                  </p>

                  <div className="flex items-center gap-3 text-[11px] text-muted-foreground pt-1">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3 text-primary" />
                      Issued: {cert.issue_date || 'N/A'}
                      {cert.expiry_date && ` · Expires: ${cert.expiry_date}`}
                    </span>
                    {cert.credential_id && (
                      <span>&bull; ID: {cert.credential_id}</span>
                    )}
                  </div>

                  {cert.credential_url && (
                    <div className="pt-1.5">
                      <a
                        href={cert.credential_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-primary hover:underline text-[11px]"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Verify Credential
                      </a>
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => handleDelete(cert.id)}
                  disabled={deletingId === cert.id}
                  className="text-muted-foreground hover:text-red-500 transition-colors p-1 rounded cursor-pointer"
                  title="Remove certification"
                  aria-label={`Remove ${cert.name}`}
                  data-testid={`delete-certification-${cert.id}`}
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
