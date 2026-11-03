import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { User } from '../api/types'
import { agent, mockApi, renderWithProviders } from '../test/utils'
import { TeamPage } from './TeamPage'

const admin: User = {
  id: 1,
  email: 'deniz@kuzey.example',
  full_name: 'Deniz Kaya',
  role: 'admin',
  is_active: true,
}

describe('TeamPage', () => {
  it('adds a staff member with the least-privileged role by default', async () => {
    const calls = mockApi((_url, init) => {
      if (init.method === 'POST') {
        return {
          status: 201,
          body: { id: 3, email: 'ece@kuzey.example', full_name: 'Ece Koç', role: 'agent_user', is_active: true },
        }
      }
      return { body: [admin, agent] }
    })
    const user = userEvent.setup()
    renderWithProviders(<TeamPage />, { user: admin })

    await user.type(screen.getByLabelText('Ad soyad'), 'Ece Koç')
    await user.type(screen.getByLabelText('E-posta'), 'ece@kuzey.example')
    await user.type(screen.getByLabelText('Geçici parola'), 'ilk giriş parolası')
    await user.click(screen.getByRole('button', { name: 'Ekle' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Ece Koç eklendi.')
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      full_name: 'Ece Koç',
      email: 'ece@kuzey.example',
      password: 'ilk giriş parolası',
      role: 'agent_user',
    })
  })

  it('offers no actions on your own row, so an admin cannot lock themselves out', async () => {
    mockApi(() => ({ body: [admin, agent] }))
    renderWithProviders(<TeamPage />, { user: admin })

    const ownRow = (await screen.findByText('Deniz Kaya')).closest('tr')!
    expect(within(ownRow).queryByRole('button')).toBeNull()
    const otherRow = screen.getByText('Selin Aydın').closest('tr')!
    expect(within(otherRow).getByRole('button', { name: 'Pasifleştir' })).toBeInTheDocument()
  })

  it('shows why a change was refused', async () => {
    mockApi((_url, init) =>
      init.method === 'PATCH'
        ? { status: 422, body: { detail: 'En az bir etkin yönetici kalmalı' } }
        : { body: [admin, agent] },
    )
    const user = userEvent.setup()
    renderWithProviders(<TeamPage />, { user: admin })

    const otherRow = (await screen.findByText('Selin Aydın')).closest('tr')!
    await user.click(within(otherRow).getByRole('button', { name: 'Pasifleştir' }))

    expect(await within(otherRow).findByRole('alert')).toHaveTextContent('En az bir etkin yönetici kalmalı')
  })
})
