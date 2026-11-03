import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import { mockApi } from '../test/utils'
import { LoginPage } from './LoginPage'

describe('LoginPage', () => {
  it('shows the server message for wrong credentials', async () => {
    mockApi(() => ({ status: 401, body: { detail: 'E-posta ya da parola hatalı' } }))
    const user = userEvent.setup()
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AuthProvider>
          <MemoryRouter>
            <LoginPage />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>,
    )

    await user.type(screen.getByLabelText('İş e-postası'), 'selin@novashop.example')
    await user.type(screen.getByLabelText('Parola'), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Giriş yap' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('E-posta ya da parola hatalı')
  })
})

describe('LoginPage in a self-hosted installation', () => {
  function renderLogin() {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/login']}>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/setup" element={<p>Kurulum sayfası</p>} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>,
    )
  }

  it('sends a fresh installation to setup', async () => {
    mockApi(() => ({
      body: { mode: 'self_hosted', setup_required: true, setup_token_required: true, organization_name: null },
    }))
    renderLogin()
    expect(await screen.findByText('Kurulum sayfası')).toBeInTheDocument()
  })

  it('names the business and never offers demo accounts', async () => {
    mockApi(() => ({
      body: {
        mode: 'self_hosted',
        setup_required: false,
        setup_token_required: true,
        organization_name: 'Kuzey Kırtasiye',
      },
    }))
    renderLogin()
    expect(await screen.findByText(/Kuzey Kırtasiye için/)).toBeInTheDocument()
    expect(screen.queryByText('Demo hesapları')).toBeNull()
  })
})
