import {
  Award,
  BookOpen,
  Briefcase,
  Calendar,
  ExternalLink,
  FolderGit2,
  Globe,
  GraduationCap,
  Link2,
  Mail,
  Phone,
  Sparkles,
  User,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { cn } from '@/lib/utils'
import type { ParsedResumeData, ResumeResponse } from '@/types/resume'

interface ResumeExtractionPreviewProps {
  resume: ResumeResponse
  className?: string
}

export function ResumeExtractionPreview({
  resume,
  className,
}: ResumeExtractionPreviewProps) {
  const parsed: ParsedResumeData | null = resume.parsed_data || null

  if (!parsed) {
    return (
      <EmptyState
        title="No structured extraction available"
        description="Parsed resume data could not be found for this document."
        className={className}
      />
    )
  }

  const { contact, skills, education, experience, projects, certifications } = parsed

  return (
    <div className={cn('space-y-6', className)} data-testid="resume-extraction-preview">
      {/* Header Metadata Banner */}
      <Card className="border-border">
        <CardHeader className="p-5 pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <CardTitle className="text-lg font-bold">
                  {contact?.full_name || resume.filename}
                </CardTitle>
                <Badge
                  variant={parsed.status === 'parsed' ? 'success' : 'outline'}
                  className="text-xs"
                >
                  {parsed.status}
                </Badge>
              </div>
              <CardDescription className="text-xs">
                Parsed from <span className="font-medium text-foreground">{resume.filename}</span> ({resume.file_type.toUpperCase()}) &bull;{' '}
                {parsed.normalized_character_count.toLocaleString()} characters normalized
              </CardDescription>
            </div>
            <div className="text-xs text-muted-foreground">
              Extracted at {new Date(parsed.extracted_at).toLocaleString()}
            </div>
          </div>
        </CardHeader>

        {/* Contact Info Row */}
        {contact && (
          <CardContent className="p-5 pt-0">
            <div className="flex flex-wrap gap-y-2 gap-x-4 text-xs text-muted-foreground border-t border-border/60 pt-3">
              {contact.full_name && (
                <div className="flex items-center gap-1.5 text-foreground font-medium">
                  <User className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  <span>{contact.full_name}</span>
                </div>
              )}
              {contact.email && (
                <a
                  href={`mailto:${contact.email}`}
                  className="flex items-center gap-1.5 hover:text-primary transition-colors"
                >
                  <Mail className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  <span>{contact.email}</span>
                </a>
              )}
              {contact.phone && (
                <a
                  href={`tel:${contact.phone}`}
                  className="flex items-center gap-1.5 hover:text-primary transition-colors"
                >
                  <Phone className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  <span>{contact.phone}</span>
                </a>
              )}
              {contact.linkedin_url && (
                <a
                  href={contact.linkedin_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="flex items-center gap-1.5 hover:text-primary transition-colors"
                >
                  <Link2 className="h-3.5 w-3.5 text-blue-600" aria-hidden="true" />
                  <span>LinkedIn</span>
                  <ExternalLink className="h-3 w-3" aria-hidden="true" />
                </a>
              )}
              {contact.github_url && (
                <a
                  href={contact.github_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="flex items-center gap-1.5 hover:text-primary transition-colors"
                >
                  <Link2 className="h-3.5 w-3.5 text-foreground" aria-hidden="true" />
                  <span>GitHub</span>
                  <ExternalLink className="h-3 w-3" aria-hidden="true" />
                </a>
              )}
              {contact.portfolio_url && (
                <a
                  href={contact.portfolio_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="flex items-center gap-1.5 hover:text-primary transition-colors"
                >
                  <Globe className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                  <span>Portfolio</span>
                  <ExternalLink className="h-3 w-3" aria-hidden="true" />
                </a>
              )}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Skills Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
              Extracted Skills
            </CardTitle>
            <span className="text-xs text-muted-foreground">
              {skills.length} skills identified
            </span>
          </div>
        </CardHeader>
        <CardContent>
          {skills.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {skills.map((skillItem, index) => (
                <Badge
                  key={index}
                  variant="secondary"
                  className="px-2.5 py-1 text-xs font-medium capitalize"
                  title={skillItem.evidence ? `Evidence: "${skillItem.evidence}"` : undefined}
                >
                  {skillItem.skill}
                  {skillItem.category && (
                    <span className="ml-1 text-[10px] text-muted-foreground opacity-80">
                      ({skillItem.category})
                    </span>
                  )}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground italic">
              No specific skill matches detected in resume text.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Experience Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <Briefcase className="h-4 w-4 text-emerald-500" aria-hidden="true" />
              Experience & Roles
            </CardTitle>
            <span className="text-xs text-muted-foreground">
              {experience.length} entries
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {experience.length > 0 ? (
            experience.map((exp, index) => (
              <div
                key={index}
                className="rounded-lg border border-border/80 bg-muted/20 p-4 space-y-2"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                  <h4 className="font-semibold text-sm text-foreground">
                    {exp.role || 'Professional Role'}
                    {exp.company && (
                      <span className="font-normal text-muted-foreground"> &bull; {exp.company}</span>
                    )}
                  </h4>
                  {(exp.start_date || exp.end_date) && (
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Calendar className="h-3 w-3" aria-hidden="true" />
                      {exp.start_date || 'Start'} – {exp.end_date || 'Present'}
                    </span>
                  )}
                </div>

                {exp.description && (
                  <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-line">
                    {exp.description}
                  </p>
                )}

                {exp.skills_used && exp.skills_used.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {exp.skills_used.map((skill, sIdx) => (
                      <span
                        key={sIdx}
                        className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-muted text-muted-foreground"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          ) : (
            <p className="text-xs text-muted-foreground italic">
              No distinct experience entries detected.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Education Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <GraduationCap className="h-4 w-4 text-blue-500" aria-hidden="true" />
              Education & Degrees
            </CardTitle>
            <span className="text-xs text-muted-foreground">
              {education.length} entries
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {education.length > 0 ? (
            education.map((edu, index) => (
              <div
                key={index}
                className="rounded-lg border border-border/80 bg-muted/20 p-4 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2"
              >
                <div>
                  <h4 className="font-semibold text-sm text-foreground">
                    {edu.degree || 'Degree Program'}
                    {edu.field_of_study && (
                      <span className="font-normal text-muted-foreground">
                        {' '}in {edu.field_of_study}
                      </span>
                    )}
                  </h4>
                  {edu.institution && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {edu.institution}
                    </p>
                  )}
                  {edu.grade && (
                    <Badge variant="outline" className="text-[11px] mt-2">
                      Grade/CGPA: {edu.grade}
                    </Badge>
                  )}
                </div>

                {(edu.start_year || edu.end_year) && (
                  <span className="text-xs text-muted-foreground shrink-0 flex items-center gap-1">
                    <Calendar className="h-3 w-3" aria-hidden="true" />
                    {edu.start_year ? `${edu.start_year} – ` : ''}
                    {edu.end_year || 'Present'}
                  </span>
                )}
              </div>
            ))
          ) : (
            <p className="text-xs text-muted-foreground italic">
              No educational credentials detected.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Projects Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <FolderGit2 className="h-4 w-4 text-amber-500" aria-hidden="true" />
              Projects
            </CardTitle>
            <span className="text-xs text-muted-foreground">
              {projects.length} entries
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {projects.length > 0 ? (
            projects.map((proj, index) => (
              <div
                key={index}
                className="rounded-lg border border-border/80 bg-muted/20 p-4 space-y-1.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-semibold text-sm text-foreground">
                    {proj.name}
                  </h4>
                  {proj.url && (
                    <a
                      href={proj.url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-xs text-primary hover:underline flex items-center gap-1"
                    >
                      <span>View</span>
                      <ExternalLink className="h-3 w-3" aria-hidden="true" />
                    </a>
                  )}
                </div>

                {proj.description && (
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {proj.description}
                  </p>
                )}

                {proj.technologies && proj.technologies.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {proj.technologies.map((tech, tIdx) => (
                      <span
                        key={tIdx}
                        className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-muted text-muted-foreground"
                      >
                        {tech}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          ) : (
            <p className="text-xs text-muted-foreground italic">
              No distinct projects detected.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Certifications Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <Award className="h-4 w-4 text-purple-500" aria-hidden="true" />
              Certifications & Credentials
            </CardTitle>
            <span className="text-xs text-muted-foreground">
              {certifications.length} entries
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {certifications.length > 0 ? (
            certifications.map((cert, index) => (
              <div
                key={index}
                className="rounded-lg border border-border/80 bg-muted/20 p-3.5 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2"
              >
                <div>
                  <h4 className="font-semibold text-sm text-foreground">
                    {cert.name}
                  </h4>
                  {cert.issuing_organization && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Issued by {cert.issuing_organization}
                    </p>
                  )}
                  {cert.credential_url && (
                    <a
                      href={cert.credential_url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-xs text-primary hover:underline flex items-center gap-1 mt-1.5"
                    >
                      <span>Credential Link</span>
                      <ExternalLink className="h-3 w-3" aria-hidden="true" />
                    </a>
                  )}
                </div>

                {cert.issue_date && (
                  <span className="text-xs text-muted-foreground shrink-0">
                    {cert.issue_date}
                  </span>
                )}
              </div>
            ))
          ) : (
            <p className="text-xs text-muted-foreground italic">
              No certifications detected.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Extraction Disclaimers & Methodology */}
      <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-xs text-muted-foreground space-y-1">
        <p className="font-semibold text-foreground flex items-center gap-1.5">
          <BookOpen className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
          Phase 11 Deterministic Extraction Architecture
        </p>
        <p>
          Phase 11 uses deterministic extraction and structured heuristics.
          Semantic matching and recommendation intelligence are implemented
          in later phases.
        </p>
      </div>
    </div>
  )
}
