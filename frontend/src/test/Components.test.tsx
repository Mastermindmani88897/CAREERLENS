import * as React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

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
import { ErrorState } from '@/components/ui/error-state'
import { Input } from '@/components/ui/input'
import { LoadingState } from '@/components/ui/loading-state'

describe('Foundational UI Components', () => {
  describe('Button Component', () => {
    it('renders with default variant and responds to click', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick}>Click Me</Button>)
      const btn = screen.getByRole('button', { name: /Click Me/i })
      expect(btn).toBeInTheDocument()

      await user.click(btn)
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('supports disabled state and prevents click event', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(
        <Button disabled onClick={handleClick}>
          Disabled
        </Button>
      )
      const btn = screen.getByRole('button', { name: /Disabled/i })
      expect(btn).toBeDisabled()

      await user.click(btn)
      expect(handleClick).not.toHaveBeenCalled()
    })

    it('renders multiple variants and sizes', () => {
      const { rerender } = render(
        <Button variant="outline" size="sm">
          Outline
        </Button>
      )
      expect(screen.getByRole('button', { name: /Outline/i })).toHaveClass(
        'border'
      )

      rerender(
        <Button variant="destructive" size="lg">
          Destructive
        </Button>
      )
      expect(
        screen.getByRole('button', { name: /Destructive/i })
      ).toHaveClass('bg-destructive')
    })
  })

  describe('Card Component', () => {
    it('renders card header, title, description, and content hierarchy', () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle>Opportunity Title</CardTitle>
            <CardDescription>Company Name &bull; Remote</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Detailed job description and required skill tags.</p>
          </CardContent>
        </Card>
      )

      expect(
        screen.getByRole('heading', { name: /Opportunity Title/i })
      ).toBeInTheDocument()
      expect(
        screen.getByText(/Company Name • Remote/i)
      ).toBeInTheDocument()
      expect(
        screen.getByText(/Detailed job description and required skill tags./i)
      ).toBeInTheDocument()
    })
  })

  describe('Input Component', () => {
    it('renders input and updates value on user change', async () => {
      const user = userEvent.setup()

      function TestInput() {
        const [val, setVal] = React.useState('')
        return (
          <Input
            placeholder="Enter skill"
            value={val}
            onChange={(e) => setVal(e.target.value)}
          />
        )
      }

      render(<TestInput />)
      const input = screen.getByPlaceholderText(/Enter skill/i)
      await user.type(input, 'TypeScript')

      expect(input).toHaveValue('TypeScript')
    })
  })

  describe('Badge Component', () => {
    it('renders badge with correct text content', () => {
      render(<Badge variant="success">Eligible</Badge>)
      expect(screen.getByText(/Eligible/i)).toBeInTheDocument()
    })
  })

  describe('State Primitives (Loading, Error, Empty)', () => {
    it('renders LoadingState with accessible message and role', () => {
      render(<LoadingState message="Fetching recommendations..." />)
      expect(screen.getByRole('status')).toBeInTheDocument()
      expect(
        screen.getByText(/Fetching recommendations.../i)
      ).toBeInTheDocument()
    })

    it('renders ErrorState with title, description, and invokes retry callback', async () => {
      const handleRetry = vi.fn()
      const user = userEvent.setup()

      render(
        <ErrorState
          title="Network Failure"
          description="Unable to contact API server."
          onRetry={handleRetry}
        />
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/Network Failure/i)).toBeInTheDocument()
      expect(
        screen.getByText(/Unable to contact API server./i)
      ).toBeInTheDocument()

      const retryBtn = screen.getByRole('button', { name: /Try Again/i })
      await user.click(retryBtn)
      expect(handleRetry).toHaveBeenCalledTimes(1)
    })

    it('renders EmptyState with custom title, message, and action button', async () => {
      const handleAction = vi.fn()
      const user = userEvent.setup()

      render(
        <EmptyState
          title="No applications found"
          description="Start applying to jobs to track your progress."
          actionLabel="Browse Jobs"
          onAction={handleAction}
        />
      )

      expect(screen.getByText(/No applications found/i)).toBeInTheDocument()
      expect(
        screen.getByText(/Start applying to jobs to track your progress./i)
      ).toBeInTheDocument()

      const actionBtn = screen.getByRole('button', { name: /Browse Jobs/i })
      await user.click(actionBtn)
      expect(handleAction).toHaveBeenCalledTimes(1)
    })
  })
})
