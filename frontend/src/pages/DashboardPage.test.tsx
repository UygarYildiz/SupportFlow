import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { User } from '../api/types'
import { mockApi, proposal, renderWithProviders } from '../test/utils'
import { DashboardPage } from './DashboardPage'

const admin: User = {
  id: 1,
  email: 'admin@novashop.example',
  full_name: 'Ada Admin',
  role: 'admin',
  is_active: true,
}

const summary = {
  by_status: { new: 9, triaging: 0, awaiting_review: 4, needs_info: 2, resolved: 3, failed: 0 },
  total: 18,
  pending_proposals: 2,
}

const address = proposal({ id: 1, ticket_id: 3, order_id: 'ORD-1003' })
const refund = proposal({
  id: 2,
  ticket_id: 2,
  order_id: 'ORD-1002',
  type: 'create_refund_request',
  payload: { refund_reason: 'damaged_item', order_total: '39.50' },
})

const audit = [
  {
    id: 10,
    actor_type: 'user',
    actor_id: 2,
    action: 'proposal.approved',
    resource_type: 'proposal',
    resource_id: '5',
    ticket_id: 15,
    details: { order_id: 'ORD-1010', status: 'approved' },
    occurred_at: '2026-11-02T10:00:00Z',
  },
  {
    id: 9,
    actor_type: 'system',
    actor_id: null,
    action: 'proposal.created',
    resource_type: 'proposal',
    resource_id: '5',
    ticket_id: 15,
    details: { order_id: 'ORD-1010', status: 'pending' },
    occurred_at: '2026-11-02T09:00:00Z',
  },
]

/** Answers like the real API, where can_decide and /audit depend on the caller's role. */
function api(role: User['role']) {
  return mockApi((url) => {
    if (url.pathname.endsWith('/tickets/summary')) return { body: summary }
    if (url.pathname.endsWith('/proposals')) {
      const items = [address, { ...refund, can_decide: role === 'admin' }]
      return { body: { items, total: 2, limit: 100, offset: 0 } }
    }
    if (url.pathname.endsWith('/tickets')) {
      return { body: { items: [], total: 0, limit: 6, offset: 0 } }
    }
    if (url.pathname.endsWith('/audit')) {
      return role === 'admin' ? { body: audit } : { status: 403, body: { detail: 'Forbidden' } }
    }
    if (url.pathname.endsWith('/users')) {
      return { body: [admin, { ...admin, id: 2, full_name: 'Sam Support', role: 'agent_user' }] }
    }
    return { status: 404, body: { detail: 'Not found' } }
  })
}

describe('DashboardPage', () => {
  it('links each status count to the filtered ticket list', async () => {
    api('agent_user')
    renderWithProviders(<DashboardPage />)

    const counter = await screen.findByRole('link', { name: /4\s*Ready for review/ })
    expect(counter).toHaveAttribute('href', '/tickets?status=awaiting_review')
  })

  it('shows an agent which requests wait for an admin, and never asks for the audit trail', async () => {
    const calls = api('agent_user')
    renderWithProviders(<DashboardPage />)

    const mine = await screen.findByRole('region', { name: /Waiting for your decision/ })
    const others = screen.getByRole('region', { name: /Waiting for an admin/ })
    expect(await within(mine).findByText('ORD-1003')).toBeInTheDocument()
    expect(within(mine).queryByText('ORD-1002')).not.toBeInTheDocument()
    expect(within(others).getByText('ORD-1002')).toBeInTheDocument()
    expect(within(others).getByText('Admin only')).toBeInTheDocument()
    expect(screen.getByText(/Only admins can see who proposed/)).toBeInTheDocument()
    expect(calls.some((c) => c.path.endsWith('/audit'))).toBe(false)
  })

  it('gives an admin every decision and the audit trail with names', async () => {
    api('admin')
    renderWithProviders(<DashboardPage />, { user: admin })

    const mine = await screen.findByRole('region', { name: /Waiting for your decision/ })
    expect(await within(mine).findByText('ORD-1002')).toBeInTheDocument()
    expect(within(mine).getByText('ORD-1003')).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: /Waiting for an admin/ })).not.toBeInTheDocument()

    const trail = screen.getByRole('region', { name: /Audit trail/ })
    expect(await within(trail).findByText('Sam Support')).toBeInTheDocument()
    expect(within(trail).getByText(/approved a change/)).toBeInTheDocument()
    expect(within(trail).getByText('AI analysis')).toBeInTheDocument()
  })

  it('shows an error instead of empty lists when proposals fail to load', async () => {
    mockApi((url) =>
      url.pathname.endsWith('/proposals')
        ? { status: 500, body: { detail: 'Database unavailable' } }
        : url.pathname.endsWith('/tickets/summary')
          ? { body: summary }
          : { body: { items: [], total: 0, limit: 6, offset: 0 } },
    )
    renderWithProviders(<DashboardPage />)

    expect(await screen.findByText(/Could not load proposals/)).toBeInTheDocument()
    expect(screen.queryByText('Nothing needs your decision right now.')).not.toBeInTheDocument()
  })
})
