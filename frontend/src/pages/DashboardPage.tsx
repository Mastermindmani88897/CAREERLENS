import { Link } from 'react-router-dom'
import {
  Briefcase,
  CheckCircle2,
  Clock,
  Compass,
  FileText,
  Sparkles,
  TrendingUp,
  Upload,
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
import { EmptyState } from '@/components/ui/empty-state'

export function DashboardPage() {
  const stats = [
    {
      label: 'Recommended Matches',
      value: '18',
      change: '+4 new today',
      icon: <Sparkles className="h-5 w-5 text-primary" aria-hidden="true" />,
    },
    {
      label: 'Active Applications',
      value: '5',
      change: '2 under review',
      icon: <Briefcase className="h-5 w-5 text-emerald-500" aria-hidden="true" />,
    },
    {
      label: 'Average Match Score',
      value: '87%',
      change: '+5% vs baseline',
      icon: <TrendingUp className="h-5 w-5 text-blue-500" aria-hidden="true" />,
    },
    {
      label: 'Interview Prep Guides',
      value: '3',
      change: 'Ready for study',
      icon: <FileText className="h-5 w-5 text-amber-500" aria-hidden="true" />,
    },
  ]

  const mockOpportunities = [
    {
      title: 'Senior Distributed Systems Engineer',
      company: 'CloudScale Technologies',
      location: 'Bengaluru, India (Hybrid)',
      score: '94%',
      status: 'High Match',
      skills: ['Go', 'Kubernetes', 'Distributed Consensus', 'PostgreSQL'],
    },
    {
      title: 'Full Stack Cloud Architect',
      company: 'Apex Digital Solutions',
      location: 'Remote, India',
      score: '89%',
      status: 'Eligible',
      skills: ['Python', 'FastAPI', 'React', 'AWS'],
    },
    {
      title: 'Machine Learning Infrastructure Engineer',
      company: 'Cognitive Data Labs',
      location: 'Bengaluru, India (Onsite)',
      score: '82%',
      status: 'Review Required',
      skills: ['Python', 'PyTorch', 'Vector Search', 'Docker'],
    },
  ]

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Career Intelligence Dashboard
            </h1>
            <Badge variant="outline" className="text-xs font-medium">
              Scaffold
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Overview of matched opportunities, eligibility evaluations, and application tracking.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/resume">
            <Button size="sm">
              <Upload className="mr-2 h-4 w-4" aria-hidden="true" />
              Upload Resume
            </Button>
          </Link>
          <Link to="/">
            <Button variant="outline" size="sm">
              <Compass className="mr-2 h-4 w-4" aria-hidden="true" />
              Explore All
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, idx) => (
          <Card key={idx}>
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {stat.label}
              </span>
              <div className="p-2 rounded-lg bg-muted/60">{stat.icon}</div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-extrabold text-foreground">
                {stat.value}
              </div>
              <p className="text-xs text-muted-foreground mt-1 flex items-center">
                <Clock className="h-3 w-3 mr-1 text-muted-foreground" aria-hidden="true" />
                {stat.change}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Top Opportunity Matches */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-foreground">
              Top Matched Opportunities
            </h2>
            <span className="text-xs text-muted-foreground">
              Sorted by Hybrid Final Score
            </span>
          </div>

          <div className="space-y-3">
            {mockOpportunities.map((opp, idx) => (
              <Card key={idx} className="hover:border-primary/50 transition-colors">
                <CardHeader className="p-5 pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle className="text-base font-semibold hover:text-primary transition-colors">
                        {opp.title}
                      </CardTitle>
                      <CardDescription className="text-xs mt-0.5">
                        {opp.company} &bull; {opp.location}
                      </CardDescription>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-lg font-bold text-primary">
                        {opp.score}
                      </div>
                      <Badge
                        variant={
                          opp.status === 'High Match'
                            ? 'success'
                            : opp.status === 'Eligible'
                              ? 'secondary'
                              : 'outline'
                        }
                        className="text-[10px] px-2 py-0"
                      >
                        {opp.status}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-5 pt-0">
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {opp.skills.map((skill, sIdx) => (
                      <span
                        key={sIdx}
                        className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-muted text-muted-foreground"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Right Column: Applications & Interview Prep Overview */}
        <div className="space-y-6">
          <div className="space-y-3">
            <h2 className="text-lg font-bold text-foreground">
              Interview Readiness
            </h2>
            <Card>
              <CardHeader className="p-5 pb-2">
                <CardTitle className="text-sm font-semibold">
                  Prepared Modules
                </CardTitle>
                <CardDescription className="text-xs">
                  Tailored question sets based on matched opportunities
                </CardDescription>
              </CardHeader>
              <CardContent className="p-5 pt-2 space-y-3 text-xs">
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-muted/40">
                  <span className="font-medium text-foreground">
                    Cloud Infrastructure Lead
                  </span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center">
                    <CheckCircle2 className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
                    Complete
                  </span>
                </div>
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-muted/40">
                  <span className="font-medium text-foreground">
                    Backend Architecture
                  </span>
                  <span className="text-muted-foreground">In Review</span>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-3">
            <h2 className="text-lg font-bold text-foreground">
              Saved Collections
            </h2>
            <EmptyState
              title="No custom lists yet"
              description="Save opportunities from your recommendations to curate custom interview target lists."
              actionLabel="Browse Recommendations"
              onAction={() => {}}
              className="p-6"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
