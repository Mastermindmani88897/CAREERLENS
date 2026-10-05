import * as React from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter, type MemoryRouterProps } from 'react-router-dom'

export interface ExtendedRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: MemoryRouterProps['initialEntries']
  routerOptions?: Omit<MemoryRouterProps, 'children'>
}

/**
 * Custom render helper that automatically wraps component with MemoryRouter.
 * Used for testing pages and components relying on React Router navigation or links.
 */
export function renderWithRouter(
  ui: React.ReactElement,
  {
    initialEntries = ['/'],
    routerOptions = {},
    ...renderOptions
  }: ExtendedRenderOptions = {}
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={initialEntries} {...routerOptions}>
        {children}
      </MemoryRouter>
    )
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  }
}

/**
 * Mock candidate/user data factory for frontend tests.
 */
export function createMockFrontendUser(overrides: Record<string, unknown> = {}) {
  return {
    id: 'f0000000-0000-0000-0000-000000000001',
    email: 'test.candidate@careerlens.local',
    fullName: 'Test Candidate',
    isActive: true,
    isSuperuser: false,
    ...overrides,
  }
}

export {
  act,
  cleanup,
  fireEvent,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
export { default as userEvent } from '@testing-library/user-event'
