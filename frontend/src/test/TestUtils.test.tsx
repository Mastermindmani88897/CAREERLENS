import { describe, expect, it } from 'vitest'
import {
  createMockFrontendUser,
  renderWithRouter,
  screen,
} from '@/test/test-utils'
import { NotFoundPage } from '@/pages/NotFoundPage'

describe('Frontend Test Utilities Foundation', () => {
  it('renderWithRouter renders components using react-router-dom Link', () => {
    renderWithRouter(<NotFoundPage />, { initialEntries: ['/non-existent'] })

    expect(
      screen.getByRole('heading', { name: /Page Not Found/i })
    ).toBeInTheDocument()

    const homeLink = screen.getByRole('link', { name: /Back to Homepage/i })
    expect(homeLink).toBeInTheDocument()
    expect(homeLink).toHaveAttribute('href', '/')
  })

  it('createMockFrontendUser provides deterministic defaults with overrides', () => {
    const defaultUser = createMockFrontendUser()
    expect(defaultUser.email).toBe('test.candidate@careerlens.local')
    expect(defaultUser.isActive).toBe(true)
    expect(defaultUser.isSuperuser).toBe(false)

    const customUser = createMockFrontendUser({
      email: 'custom.lead@careerlens.local',
      fullName: 'Lead Engineer',
      isSuperuser: true,
    })
    expect(customUser.email).toBe('custom.lead@careerlens.local')
    expect(customUser.fullName).toBe('Lead Engineer')
    expect(customUser.isSuperuser).toBe(true)
  })
})
