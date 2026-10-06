import * as React from 'react'
import { FileText, Sparkles, Upload } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { ResumeExtractionPreview } from '@/components/resume/ResumeExtractionPreview'
import { ResumeUploadCard } from '@/components/resume/ResumeUploadCard'
import type { ResumeResponse } from '@/types/resume'

export function ResumePage() {
  const [activeResume, setActiveResume] = React.useState<ResumeResponse | null>(null)

  return (
    <div className="space-y-8 pb-12">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Resume Parsing & Intelligence
            </h1>
            <Badge variant="outline" className="text-xs font-medium">
              Phase 11
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Deterministic resume ingestion and structured data extraction pipeline.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="text-xs py-1 px-2.5">
            <FileText className="mr-1.5 h-3.5 w-3.5 text-primary" aria-hidden="true" />
            PDF &bull; DOCX &bull; TXT
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Upload Card */}
        <div className={activeResume ? 'lg:col-span-5' : 'lg:col-span-8 lg:col-start-3'}>
          <ResumeUploadCard
            onUploadSuccess={(resume) => setActiveResume(resume)}
          />

          {!activeResume && (
            <div className="mt-6 rounded-xl border border-dashed border-border/80 p-6 text-center text-xs text-muted-foreground space-y-2">
              <div className="flex justify-center">
                <div className="rounded-full bg-primary/10 p-2.5 text-primary">
                  <Sparkles className="h-4 w-4" aria-hidden="true" />
                </div>
              </div>
              <p className="font-semibold text-foreground">
                Deterministic Extraction Guarantee
              </p>
              <p className="max-w-md mx-auto">
                Phase 11 uses deterministic extraction and structured heuristics.
                Semantic matching and recommendation intelligence are implemented
                in later phases.
              </p>
            </div>
          )}
        </div>

        {/* Right Column: Parsed Results Preview */}
        {activeResume && (
          <div className="lg:col-span-7">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                <Upload className="h-4 w-4 text-primary" aria-hidden="true" />
                Extracted Career Profile
              </h2>
              <span className="text-xs text-muted-foreground">
                Document ID: {activeResume.id.slice(0, 8)}...
              </span>
            </div>

            <ResumeExtractionPreview resume={activeResume} />
          </div>
        )}
      </div>
    </div>
  )
}
