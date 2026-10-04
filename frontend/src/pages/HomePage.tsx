import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Briefcase,
  CheckCircle2,
  FileText,
  Layers,
  Sparkles,
  Target,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export function HomePage() {
  const features = [
    {
      icon: <Target className="h-6 w-6 text-primary" aria-hidden="true" />,
      title: 'Hybrid Match Intelligence',
      description:
        'Combines semantic vector embeddings (pgvector) with deterministic rule scoring across skills, experience, education, and location.',
      tag: 'Core Engine',
    },
    {
      icon: <Layers className="h-6 w-6 text-primary" aria-hidden="true" />,
      title: 'Explainable Skill-Gaps',
      description:
        'Clear, honest breakdowns of required vs. preferred competencies with actionable guidance on addressing missing skills.',
      tag: 'Transparency',
    },
    {
      icon: <FileText className="h-6 w-6 text-primary" aria-hidden="true" />,
      title: 'Tailored Interview Prep',
      description:
        'Contextual technical and behavioral questions generated directly from candidate profile and opportunity requirements.',
      tag: 'Preparation',
    },
  ]

  const highlights = [
    'PostgreSQL 18.6 with native pgvector cosine similarity',
    'SQLAlchemy 2.x async architecture with least-privilege security',
    'Strict relational data integrity with ON DELETE CASCADE guarantees',
    'Bcrypt salted authentication and RFC-compliant Bearer JWTs',
  ]

  return (
    <div className="space-y-16 py-4">
      {/* Hero Section */}
      <section className="text-center space-y-6 max-w-4xl mx-auto pt-6 pb-4">
        <div className="inline-flex items-center gap-2">
          <Badge variant="outline" className="px-3 py-1 text-xs font-medium border-primary/30 bg-primary/5 text-primary">
            <Sparkles className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
            Next-Gen Career Intelligence
          </Badge>
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground leading-[1.15]">
          Intelligent Job Matching with{' '}
          <span className="text-primary bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
            Total Transparency
          </span>
        </h1>

        <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          CareerLens evaluates candidate profiles against real opportunities using a
          hybrid deterministic and semantic scoring pipeline.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Link to="/register">
            <Button size="lg" className="w-full sm:w-auto font-semibold shadow-md">
              Get Started
              <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
            </Button>
          </Link>
          <Link to="/dashboard">
            <Button variant="outline" size="lg" className="w-full sm:w-auto font-semibold">
              <Briefcase className="mr-2 h-4 w-4" aria-hidden="true" />
              Explore Dashboard
            </Button>
          </Link>
        </div>
      </section>

      {/* Feature Cards Grid */}
      <section className="space-y-6">
        <div className="text-center max-w-xl mx-auto space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Built for Modern Job Seekers
          </h2>
          <p className="text-sm text-muted-foreground">
            A reliable, normalized architecture designed for precision and explainability.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
          {features.map((feature, idx) => (
            <Card key={idx} className="hover:border-primary/50 transition-all hover:shadow-md">
              <CardHeader className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                    {feature.icon}
                  </div>
                  <Badge variant="secondary" className="text-xs">
                    {feature.tag}
                  </Badge>
                </div>
                <CardTitle className="text-lg font-bold">{feature.title}</CardTitle>
                <CardDescription className="text-sm leading-relaxed">
                  {feature.description}
                </CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>

      {/* Architecture Highlights Banner */}
      <section className="rounded-2xl border border-border bg-card p-8 sm:p-10 shadow-sm">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
          <div className="space-y-4">
            <Badge variant="outline" className="text-xs font-semibold">
              Verified Technical Foundation
            </Badge>
            <h3 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
              Enterprise-Grade Database & Backend Stack
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Every layer of CareerLens is engineered with verified benchmarks, comprehensive automated test suites, and strict separation of concerns.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {highlights.map((item, idx) => (
              <div
                key={idx}
                className="flex items-start space-x-3 p-3.5 rounded-lg border border-border/60 bg-background/50 text-xs sm:text-sm font-medium"
              >
                <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" aria-hidden="true" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
