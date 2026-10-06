import * as React from 'react'
import {
  CheckCircle2,
  FileCheck,
  FileText,
  Loader2,
  UploadCloud,
  X,
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
import { cn } from '@/lib/utils'
import {
  ALLOWED_EXTENSIONS,
  uploadResume,
  validateResumeFile,
} from '@/services/resumeService'
import type { ResumeResponse } from '@/types/resume'
import { ResumeErrorAlert } from './ResumeErrorAlert'

interface ResumeUploadCardProps {
  onUploadSuccess?: (resume: ResumeResponse) => void
  className?: string
}

export function ResumeUploadCard({
  onUploadSuccess,
  className,
}: ResumeUploadCardProps) {
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null)
  const [isDragging, setIsDragging] = React.useState(false)
  const [isUploading, setIsUploading] = React.useState(false)
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)
  const [uploadedResume, setUploadedResume] = React.useState<ResumeResponse | null>(null)

  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const handleFileSelection = (file: File) => {
    setErrorMessage(null)
    setUploadedResume(null)

    const validation = validateResumeFile(file)
    if (!validation.isValid) {
      setErrorMessage(validation.error || 'Invalid file.')
      setSelectedFile(null)
      return
    }

    setSelectedFile(file)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelection(e.target.files[0])
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0])
    }
  }

  const handleClearFile = () => {
    setSelectedFile(null)
    setErrorMessage(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setIsUploading(true)
    setErrorMessage(null)

    try {
      const result = await uploadResume(selectedFile)
      setUploadedResume(result)
      if (onUploadSuccess) {
        onUploadSuccess(result)
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed.'
      setErrorMessage(message)
    } finally {
      setIsUploading(false)
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  return (
    <Card className={cn('shadow-sm border-border', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-bold tracking-tight">
            Resume Ingestion & Parsing
          </CardTitle>
          <Badge variant="outline" className="text-xs">
            Phase 11 Pipeline
          </Badge>
        </div>
        <CardDescription className="text-sm">
          Upload your resume in PDF, DOCX, or TXT format. Our deterministic parsing engine
          will extract contact details, skills, education, experience, and projects.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Drag and drop zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={cn(
            'flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-colors cursor-pointer',
            isDragging
              ? 'border-primary bg-primary/5 scale-[1.005]'
              : 'border-border/80 hover:border-primary/50 hover:bg-muted/30',
            isUploading && 'pointer-events-none opacity-60'
          )}
          role="button"
          tabIndex={0}
          aria-label="Upload resume file dropzone"
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              fileInputRef.current?.click()
            }
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ALLOWED_EXTENSIONS.join(',')}
            onChange={handleInputChange}
            className="hidden"
            data-testid="resume-file-input"
          />

          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary mb-3">
            <UploadCloud className="h-6 w-6" aria-hidden="true" />
          </div>

          <p className="text-sm font-semibold text-foreground">
            Click to upload or drag and drop your resume
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Supported formats: PDF, DOCX, TXT (Maximum file size: 10 MB)
          </p>
        </div>

        {/* Selected file preview */}
        {selectedFile && !uploadedResume && (
          <div
            className="flex items-center justify-between rounded-lg border border-border bg-muted/40 p-3.5 text-sm"
            data-testid="selected-file-preview"
          >
            <div className="flex items-center space-x-3 overflow-hidden">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <FileText className="h-5 w-5" aria-hidden="true" />
              </div>
              <div className="truncate">
                <p className="font-medium text-foreground truncate" title={selectedFile.name}>
                  {selectedFile.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2 shrink-0">
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation()
                  handleClearFile()
                }}
                disabled={isUploading}
                aria-label="Remove selected file"
                className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        )}

        {/* Error message */}
        {errorMessage && (
          <ResumeErrorAlert
            error={errorMessage}
            onRetry={selectedFile ? handleUpload : undefined}
          />
        )}

        {/* Success message */}
        {uploadedResume && (
          <div
            role="status"
            className="flex items-start gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-900 dark:text-emerald-200"
            data-testid="upload-success-banner"
          >
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600 dark:text-emerald-400 mt-0.5" aria-hidden="true" />
            <div className="space-y-1">
              <p className="font-semibold">
                Resume successfully parsed!
              </p>
              <p className="text-xs opacity-90">
                Extraction completed for <strong>{uploadedResume.filename}</strong>. Review your structured career data below.
              </p>
              <div className="pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearFile}
                  className="h-7 text-xs border-emerald-500/30 hover:bg-emerald-500/20"
                >
                  Upload Another Document
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Action Button */}
        {selectedFile && !uploadedResume && (
          <div className="flex justify-end pt-2">
            <Button
              onClick={handleUpload}
              disabled={isUploading}
              className="w-full sm:w-auto"
              data-testid="upload-submit-button"
            >
              {isUploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                  Extracting Resume...
                </>
              ) : (
                <>
                  <FileCheck className="mr-2 h-4 w-4" aria-hidden="true" />
                  Parse Resume
                </>
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
