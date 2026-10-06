import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import App from '@/App'

describe('CareerLens Application Shell & Routing', () => {
  it('renders application brand in navbar', () => {
    render(<App />)
    const brandElements = screen.getAllByText(/CareerLens/i)
    expect(brandElements.length).toBeGreaterThan(0)
  })

  it('renders root landing page with primary headline and CTAs', () => {
    render(<App />)
    expect(
      screen.getByRole('heading', {
        name: /Intelligent Job Matching with Total Transparency/i,
      })
    ).toBeInTheDocument()

    expect(
      screen.getAllByRole('button', { name: /Get Started/i })[0]
    ).toBeInTheDocument()
  })

  it('renders foundational feature cards on homepage', () => {
    render(<App />)
    expect(
      screen.getByText(/Hybrid Match Intelligence/i)
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Explainable Skill-Gaps/i)
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Tailored Interview Prep/i)
    ).toBeInTheDocument()
  })

  it('navigates to login page via navigation link', async () => {
    const user = userEvent.setup()
    render(<App />)

    const signInButtons = screen.getAllByRole('button', { name: /Sign In/i })
    await user.click(signInButtons[0])

    expect(
      screen.getByRole('heading', { name: /Sign In to CareerLens/i })
    ).toBeInTheDocument()
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument()
  })

  it('navigates to register page and displays password policy', async () => {
    const user = userEvent.setup()
    render(<App />)

    const getStartedButtons = screen.getAllByRole('button', {
      name: /Get Started/i,
    })
    await user.click(getStartedButtons[0])

    expect(
      screen.getByRole('heading', { name: /Create an Account/i })
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Password Security Policy:/i)
    ).toBeInTheDocument()
    expect(screen.getByLabelText(/Confirm Password/i)).toBeInTheDocument()
  })

  it('navigates to dashboard and displays match overview', async () => {
    const user = userEvent.setup()
    render(<App />)

    const dashboardLink = screen.getAllByRole('link', {
      name: /Dashboard/i,
    })[0]
    await user.click(dashboardLink)

    expect(
      screen.getByRole('heading', { name: /Career Intelligence Dashboard/i })
    ).toBeInTheDocument()
    expect(screen.getByText(/Recommended Matches/i)).toBeInTheDocument()
    expect(screen.getByText(/Active Applications/i)).toBeInTheDocument()
  })

  it('renders 404 error page for unmatched routes', () => {
    window.history.pushState({}, '', '/non-existent-route-12345')
    render(<App />)

    expect(screen.getByText(/404 Error/i)).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /Page Not Found/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Back to Homepage/i })
    ).toBeInTheDocument()
  })

  it('navigates to profile page via navigation link', async () => {
    const user = userEvent.setup()
    render(<App />)

    const profileLinks = screen.getAllByRole('link', {
      name: /Profile/i,
    })
    expect(profileLinks.length).toBeGreaterThan(0)
    await user.click(profileLinks[0])

    expect(
      await screen.findByTestId(/(profile-loading|profile-error|candidate-profile-page)/)
    ).toBeInTheDocument()
  })

  it('never displays sensitive credentials or server secrets in rendered UI', () => {
    const { container } = render(<App />)
    const html = container.innerHTML

    expect(html).not.toMatch(/JWT_SECRET/i)
    expect(html).not.toMatch(/PGPASSWORD/i)
    expect(html).not.toMatch(/careerlens_user/i)
    expect(html).not.toMatch(/M@ni88897/i)
  })
})
