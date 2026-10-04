import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'

const CURRENT_YEAR = new Date().getFullYear()

export function Footer() {
  return (
    <footer className="w-full border-t border-border bg-card/50 text-muted-foreground text-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand info */}
          <div className="space-y-3 md:col-span-2">
            <div className="flex items-center space-x-2 font-bold text-lg text-foreground">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Compass className="h-4 w-4" aria-hidden="true" />
              </div>
              <span>CareerLens</span>
            </div>
            <p className="text-sm text-muted-foreground max-w-sm">
              Intelligent job recommendations, hybrid deterministic matching, and career progression intelligence.
            </p>
          </div>

          {/* Platform Links */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground">
              Platform
            </h4>
            <ul className="space-y-1.5">
              <li>
                <Link to="/" className="hover:text-foreground transition-colors">
                  Home
                </Link>
              </li>
              <li>
                <Link to="/dashboard" className="hover:text-foreground transition-colors">
                  Dashboard
                </Link>
              </li>
            </ul>
          </div>

          {/* Authentication Links */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground">
              Account
            </h4>
            <ul className="space-y-1.5">
              <li>
                <Link to="/login" className="hover:text-foreground transition-colors">
                  Sign In
                </Link>
              </li>
              <li>
                <Link to="/register" className="hover:text-foreground transition-colors">
                  Create Account
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="pt-6 border-t border-border/60 flex flex-col sm:flex-row items-center justify-between text-xs gap-3">
          <p>&copy; {CURRENT_YEAR} CareerLens. All rights reserved.</p>
          <p className="text-muted-foreground">
            Built with React, Vite, and Tailwind CSS.
          </p>
        </div>
      </div>
    </footer>
  )
}
