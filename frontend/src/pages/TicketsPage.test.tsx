import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { mockApi, renderWithProviders } from '../test/utils'
import { TicketsPage } from './TicketsPage'

const emptySummary = {
  by_status: { new: 0, triaging: 0, awaiting_review: 0, needs_info: 0, resolved: 0, failed: 0 },
  total: 0,
  pending_proposals: 0,
}

describe('TicketsPage', () => {
  it('explains an empty inbox instead of showing an empty table', async () => {
    mockApi((url) =>
      url.pathname.endsWith('/summary')
        ? { body: emptySummary }
        : { body: { items: [], total: 0, limit: 25, offset: 0 } },
    )
    renderWithProviders(<TicketsPage />)

    expect(await screen.findByText('Burada talep yok.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('shows a clear error when the API fails', async () => {
    mockApi(() => ({ status: 500, body: { detail: 'Veritabanına ulaşılamıyor' } }))
    renderWithProviders(<TicketsPage />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Talepler yüklenemedi')
  })

  it('points to decisions that are waiting', async () => {
    mockApi((url) =>
      url.pathname.endsWith('/summary')
        ? { body: { ...emptySummary, pending_proposals: 2 } }
        : { body: { items: [], total: 0, limit: 25, offset: 0 } },
    )
    renderWithProviders(<TicketsPage />)

    expect(await screen.findByRole('link', { name: /Karar bekleyen 2 sipariş değişikliği/ })).toHaveAttribute(
      'href',
      '/approvals',
    )
  })
})
