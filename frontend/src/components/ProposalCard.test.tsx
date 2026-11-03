import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { mockApi, proposal, renderWithProviders } from '../test/utils'
import { ProposalCard } from './ProposalCard'

describe('ProposalCard', () => {
  it('shows the change before and after, and who may decide', () => {
    renderWithProviders(<ProposalCard proposal={proposal()} />)

    expect(screen.getByText('Atatürk Cad. No:93, Karşıyaka/İzmir')).toBeInTheDocument()
    expect(screen.getByText('Kordon Sok. No:15, Bornova/İzmir')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Onayla ve uygula' })).toBeEnabled()
  })

  it('sends the version it was shown and blocks a second click while applying', async () => {
    let release: () => void = () => {}
    const calls = mockApi(() => ({ body: proposal({ status: 'executed', version: 4 }) }))
    const user = userEvent.setup()
    renderWithProviders(<ProposalCard proposal={proposal({ version: 1 })} />)

    // Hold the request open so we can inspect the in-flight state.
    const gate = new Promise<void>((resolve) => (release = resolve))
    const original = globalThis.fetch
    globalThis.fetch = async (...args: Parameters<typeof fetch>) => {
      await gate
      return original(...args)
    }

    await user.click(screen.getByRole('button', { name: 'Onayla ve uygula' }))
    expect(screen.getByRole('button', { name: 'Uygulanıyor…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reddet' })).toBeDisabled()

    release()
    await waitFor(() => expect(calls).toHaveLength(1))
    expect(calls[0]).toMatchObject({
      method: 'POST',
      path: '/api/v1/proposals/7/decision',
      body: { decision: 'approve', expected_version: 1 },
    })
  })

  it('reports a conflict instead of pretending it worked', async () => {
    mockApi(() => ({
      status: 409,
      body: { detail: "7 numaralı öneri zaten 'executed' durumunda" },
    }))
    const user = userEvent.setup()
    renderWithProviders(<ProposalCard proposal={proposal()} />)

    await user.click(screen.getByRole('button', { name: 'Onayla ve uygula' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent("zaten 'executed'")
    expect(screen.queryByText('ONAYLANDI')).not.toBeInTheDocument()
  })

  it('offers no decision buttons to a role that may not decide', () => {
    renderWithProviders(
      <ProposalCard
        proposal={proposal({ type: 'create_refund_request', can_decide: false, payload: {} })}
      />,
    )

    expect(screen.queryByRole('button', { name: 'Onayla ve uygula' })).not.toBeInTheDocument()
    expect(screen.getByText('İade talepleri hakkında yalnızca yönetici karar verebilir.')).toBeInTheDocument()
    // Marked before anyone opens it, so the rule is visible on the queue too.
    expect(screen.getByText('Yalnızca yönetici')).toBeInTheDocument()
  })

  it('stamps decided proposals', () => {
    renderWithProviders(<ProposalCard proposal={proposal({ status: 'executed', version: 4 })} />)
    expect(screen.getByText('ONAYLANDI')).toBeInTheDocument()
    expect(screen.getByText('Uygulandı')).toBeInTheDocument()
  })
})
