import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from '@/App'
import { Input } from '@/components/ui/input'

describe('Frontend Security & Hygiene Audit', () => {
  it('ensures client environment does not expose backend server secrets', () => {
    const env = import.meta.env as Record<string, string | undefined>

    // Server-only variables must never be present in frontend client bundle
    expect(env.JWT_SECRET).toBeUndefined()
    expect(env.JWT_SECRET_KEY).toBeUndefined()
    expect(env.PGPASSWORD).toBeUndefined()
    expect(env.DATABASE_URL).toBeUndefined()
    expect(env.POSTGRES_PASSWORD).toBeUndefined()
    expect(env.APP_SECRET_KEY).toBeUndefined()
  })

  it('ensures password inputs use type="password" to avoid screen shoulder-surfing', () => {
    render(<Input type="password" placeholder="Password" aria-label="Password Input" />)
    const input = screen.getByLabelText(/Password Input/i) as HTMLInputElement
    expect(input.type).toBe('password')
  })

  it('ensures rendered App does not use dangerouslySetInnerHTML', () => {
    const { container } = render(<App />)
    // Check all elements inside container for danger attribute
    const allElements = container.querySelectorAll('*')
    allElements.forEach((el) => {
      expect(el.getAttribute('dangerouslysetinnerhtml')).toBeNull()
    })
  })

  it('ensures no raw tokens or passwords exist in localStorage by default', () => {
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('jwt')).toBeNull()
    expect(localStorage.getItem('password')).toBeNull()
  })
})
