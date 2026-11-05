import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../api/types'
import { RequireAuth } from '../app/RequireAuth'
import { AuthContext } from '../auth/context'
import { agent, mockApi } from '../test/utils'

function renderAt(route: string, user: User | undefined) {
  const auth = { user, isLoading: false, signIn: vi.fn(), acceptToken: vi.fn(), signOut: vi.fn() }
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route path="/login" element={<p>Giriş ekranı</p>} />
            <Route
              path="*"
              element={
                <RequireAuth>
                  <p>Panel</p>
                </RequireAuth>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  )
}

function demoBuild() {
  vi.stubEnv('DEV', false)
  vi.stubEnv('VITE_DEMO_MODE', 'true')
}

function selfHostedBuild() {
  vi.stubEnv('DEV', false)
  vi.stubEnv('VITE_DEMO_MODE', 'false')
}

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('Landing page', () => {
  it('greets signed-out visitors of the demo and wakes the backend', () => {
    demoBuild()
    const calls = mockApi(() => ({ body: { status: 'ok' } }))
    renderAt('/', undefined)

    expect(
      screen.getByRole('heading', { level: 1, name: /son sözü siz söylersiniz/ }),
    ).toBeInTheDocument()
    for (const link of screen.getAllByRole('link', { name: 'Canlı demoyu dene' })) {
      expect(link).toHaveAttribute('href', '/login')
    }
    expect(screen.getByRole('link', { name: 'Kendi sunucuna kur' })).toHaveAttribute(
      'href',
      expect.stringContaining('docs/SELF_HOSTING.md'),
    )
    expect(calls.map((call) => call.path)).toContain('/health')
  })

  it('never appears in a self-hosted installation', () => {
    selfHostedBuild()
    renderAt('/', undefined)

    expect(screen.getByText('Giriş ekranı')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 1 })).not.toBeInTheDocument()
  })

  it('only replaces the home page; other pages still ask for a login', () => {
    demoBuild()
    renderAt('/tickets', undefined)

    expect(screen.getByText('Giriş ekranı')).toBeInTheDocument()
  })

  it('sends signed-in staff straight to the dashboard', () => {
    demoBuild()
    renderAt('/', agent)

    expect(screen.getByText('Panel')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 1 })).not.toBeInTheDocument()
  })
})
