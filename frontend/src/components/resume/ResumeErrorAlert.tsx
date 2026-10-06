import * as React from 'react'
import { AlertCircle, FileWarning, RefreshCw, ShieldAlert } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface ResumeErrorAlertProps extends React.HTMLAttributes<HTMLDivElement> {
  error: string
  onRetry?: () => void
}

/**
 * Categorize error messages for contextual styling and tips.
 */
function getErrorDetails(errorMsg: string) {
  const lower = errorMsg.toLowerCase()
  if (lower.includes('unsupported') || lower.includes('format') || lower.includes('extension')) {
    return {
      title: 'Unsupported File Format',
      suggestion: 'Only .pdf, .docx, and .txt files are supported. Image or executable formats cannot be parsed.',
      icon: <FileWarning className="h-5 w-5 text-amber-500" aria-hidden="true" />,
    }
  }
  if (lower.includes('size') || lower.includes('limit') || lower.includes('10 mb')) {
    return {
      title: 'File Size Exceeded',
      suggestion: 'The maximum allowed file size is 10 MB. Please compress or optimize your document before uploading.',
      icon: <FileWarning className="h-5 w-5 text-amber-500" aria-hidden="true" />,
    }
  }
  if (lower.includes('scanned') || lower.includes('ocr') || lower.includes('no extractable text')) {
    return {
      title: 'No Extractable Text',
      suggestion: 'Scanned image-only PDFs without digital text layers cannot be extracted. Please upload a searchable text PDF or DOCX.',
      icon: <FileWarning className="h-5 w-5 text-amber-500" aria-hidden="true" />,
    }
  }
  if (lower.includes('password') || lower.includes('encrypted')) {
    return {
      title: 'Password Protected Document',
      suggestion: 'Encrypted or password-protected files cannot be read. Please remove the password protection and re-upload.',
      icon: <ShieldAlert className="h-5 w-5 text-destructive" aria-hidden="true" />,
    }
  }
  if (lower.includes('auth') || lower.includes('sign in')) {
    return {
      title: 'Authentication Required',
      suggestion: 'Your session may have expired. Please sign in to authenticate your resume upload.',
      icon: <ShieldAlert className="h-5 w-5 text-destructive" aria-hidden="true" />,
    }
  }
  return {
    title: 'Resume Processing Error',
    suggestion: 'An error occurred during extraction. Please verify your document is not corrupt.',
    icon: <AlertCircle className="h-5 w-5 text-destructive" aria-hidden="true" />,
  }
}

export function ResumeErrorAlert({
  error,
  onRetry,
  className,
  ...props
}: ResumeErrorAlertProps) {
  const details = getErrorDetails(error)

  return (
    <div
      role="alert"
      className={cn(
        'rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm',
        className
      )}
      {...props}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0">{details.icon}</div>
        <div className="flex-1 space-y-1">
          <h4 className="font-semibold text-foreground">{details.title}</h4>
          <p className="text-muted-foreground">{error}</p>
          <p className="text-xs text-muted-foreground/80 mt-1">{details.suggestion}</p>

          {onRetry && (
            <div className="pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="h-8 border-destructive/30 hover:bg-destructive/10 text-xs"
              >
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                Try Again
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
