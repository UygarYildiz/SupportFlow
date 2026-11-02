import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router'
import { vi } from 'vitest'
import type { Proposal, User } from '../api/types'
import { AuthContext } from '../auth/context'

type Handler = (url: URL, init: RequestInit) => { status?: number; body: unknown }

/** Replace fetch with a small router: each test answers only the calls it expects. */
export function mockApi(handler: Handler) {
  const calls: { method: string; path: string; body: unknown }[] = []
  const fetchMock = vi.fn(async (input: string, init: RequestInit = {}) => {
    const url = new URL(input, 'http://localhost')
    const body = init.body ? JSON.parse(String(init.body)) : undefined
    calls.push({ method: init.method ?? 'GET', path: url.pathname, body })
    const result = handler(url, init)
    return new Response(JSON.stringify(result.body), {
      status: result.status ?? 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  return calls
}

export const agent: User = {
  id: 2,
  email: 'sam@novashop.example',
  full_name: 'Sam Support',
  role: 'agent_user',
  is_active: true,
}

export function renderWithProviders(ui: ReactNode, { user = agent, route = '/' } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const auth = { user, isLoading: false, signIn: vi.fn(), signOut: vi.fn() }
  return render(
    <QueryClientProvider client={client}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  )
}

export function proposal(overrides: Partial<Proposal> = {}): Proposal {
  return {
    id: 7,
    ticket_id: 15,
    run_id: 3,
    order_id: 'ORD-1010',
    type: 'change_shipping_address',
    payload: { current_address: '93 Station Rd, Riverton', new_address: '15 Station Rd, Brookfield' },
    reason: 'Order has not shipped yet; the shipping address can be changed.',
    policy_rule: 'address_change_v1',
    status: 'pending',
    version: 1,
    created_at: '2026-11-02T10:00:00Z',
    expires_at: '2026-11-04T10:00:00Z',
    decided_by: null,
    decided_at: null,
    decision_note: null,
    executed_at: null,
    failure_reason: null,
    can_decide: true,
    ...overrides,
  }
}
