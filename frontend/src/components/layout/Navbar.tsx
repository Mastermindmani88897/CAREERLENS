import * as React from 'react'
import { Link, NavLink } from 'react-router-dom'
import { Compass, Menu, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)

  const navLinks = [
    { to: '/', label: 'Home' },
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/resume', label: 'Resume' },
  ]

  const closeMobileMenu = () => setMobileMenuOpen(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/80 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand Logo */}
        <Link
          to="/"
          className="flex items-center space-x-2.5 font-bold text-xl tracking-tight text-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
          onClick={closeMobileMenu}
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Compass className="h-5 w-5" aria-hidden="true" />
          </div>
          <span>CareerLens</span>
        </Link>

        {/* Desktop Navigation Links */}
        <nav
          className="hidden md:flex items-center space-x-6 text-sm font-medium"
          aria-label="Main Navigation"
        >
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                cn(
                  'transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded px-2 py-1',
                  isActive
                    ? 'text-primary font-semibold'
                    : 'text-muted-foreground'
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        {/* Desktop Auth CTA */}
        <div className="hidden md:flex items-center space-x-3">
          <Link to="/login">
            <Button variant="ghost" size="sm">
              Sign In
            </Button>
          </Link>
          <Link to="/register">
            <Button size="sm">Get Started</Button>
          </Link>
        </div>

        {/* Mobile Menu Toggle Button */}
        <div className="flex md:hidden">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-expanded={mobileMenuOpen}
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? (
              <X className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Menu className="h-5 w-5" aria-hidden="true" />
            )}
          </Button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-border bg-background px-4 pt-2 pb-6 space-y-3 animate-in slide-in-from-top-2 duration-200">
          <nav
            className="flex flex-col space-y-2 pt-2"
            aria-label="Mobile Navigation"
          >
            {navLinks.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                onClick={closeMobileMenu}
                className={({ isActive }) =>
                  cn(
                    'block px-3 py-2 rounded-md text-base font-medium transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary font-semibold'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex flex-col space-y-2 pt-4 border-t border-border">
            <Link to="/login" onClick={closeMobileMenu} className="w-full">
              <Button variant="outline" className="w-full justify-center">
                Sign In
              </Button>
            </Link>
            <Link to="/register" onClick={closeMobileMenu} className="w-full">
              <Button className="w-full justify-center">Get Started</Button>
            </Link>
          </div>
        </div>
      )}

    </header>
  )
}
