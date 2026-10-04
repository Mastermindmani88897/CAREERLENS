import { Link } from 'react-router-dom'
import { ArrowLeft, FileQuestion } from 'lucide-react'

import { Button } from '@/components/ui/button'

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-16 sm:py-24 text-center px-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary mb-6">
        <FileQuestion className="h-8 w-8" aria-hidden="true" />
      </div>

      <span className="text-sm font-bold uppercase tracking-wider text-primary mb-2">
        404 Error
      </span>
      <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground mb-3">
        Page Not Found
      </h1>
      <p className="text-base text-muted-foreground max-w-md mb-8">
        The page you are looking for does not exist or has been moved. Check the URL or return to the CareerLens homepage.
      </p>

      <Link to="/">
        <Button size="lg" className="font-semibold shadow-sm">
          <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
          Back to Homepage
        </Button>
      </Link>
    </div>
  )
}
