import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
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
