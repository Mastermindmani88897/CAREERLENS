import * as React from 'react'
import { Link } from 'react-router-dom'
import { Info, Lock, Mail, ShieldCheck } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'

export function RegisterPage() {
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [confirmPassword, setConfirmPassword] = React.useState('')
  const [submitted, setSubmitted] = React.useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
  }

  return (
    <div className="flex flex-col items-center justify-center py-6 sm:py-12">
      <div className="w-full max-w-md space-y-6">
        <Card className="shadow-lg border-border">
          <CardHeader className="space-y-1 text-center">
            <CardTitle className="text-2xl font-bold tracking-tight">
              Create an Account
            </CardTitle>
            <CardDescription className="text-sm">
              Sign up to discover matched opportunities and analyze skill gaps
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit} noValidate>
            <CardContent className="space-y-4">
              {/* Notice Banner */}
              <div className="flex items-start space-x-2.5 rounded-lg border border-blue-500/20 bg-blue-500/10 p-3 text-xs text-blue-700 dark:text-blue-300">
                <Info className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
                <p>
                  <strong>Phase 7 Scaffold:</strong> Frontend registration UI is decoupled from the backend during this foundation phase.
                </p>
              </div>

              {submitted && (
                <div
                  role="status"
                  className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-800 dark:text-emerald-300"
                >
                  Registration inputs verified locally. Backend user creation will be connected in a later phase.
                </div>
              )}

              {/* Email Field */}
              <div className="space-y-1.5">
                <label
                  htmlFor="register-email"
                  className="text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                >
                  Email Address
                </label>
                <div className="relative">
                  <Input
                    id="register-email"
                    type="email"
                    autoComplete="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                  <Mail
                    className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground"
                    aria-hidden="true"
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className="space-y-1.5">
                <label
                  htmlFor="register-password"
                  className="text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                >
                  Password
                </label>
                <div className="relative">
                  <Input
                    id="register-password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Minimum 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <Lock
                    className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground"
                    aria-hidden="true"
                  />
                </div>
              </div>

              {/* Confirm Password Field */}
              <div className="space-y-1.5">
                <label
                  htmlFor="register-confirm-password"
                  className="text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                >
                  Confirm Password
                </label>
                <div className="relative">
                  <Input
                    id="register-confirm-password"
                    type="password"
                    autoComplete="new-password"
                    placeholder="Re-enter password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                  />
                  <ShieldCheck
                    className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground"
                    aria-hidden="true"
                  />
                </div>
              </div>

              <div className="rounded-md bg-muted/60 p-3 text-xs text-muted-foreground">
                <p className="font-medium text-foreground mb-1">
                  Password Security Policy:
                </p>
                <ul className="list-disc pl-4 space-y-0.5">
                  <li>At least 8 characters in length</li>
                  <li>Bcrypt-compatible format (maximum 72 bytes)</li>
                </ul>
              </div>
            </CardContent>

            <CardFooter className="flex flex-col space-y-4">
              <Button type="submit" className="w-full font-semibold">
                Create Account
              </Button>
              <p className="text-center text-xs text-muted-foreground">
                Already have an account?{' '}
                <Link
                  to="/login"
                  className="font-medium text-primary hover:underline"
                >
                  Sign in
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  )
}
