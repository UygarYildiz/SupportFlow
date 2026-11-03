import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { PolicyCheck, PolicyExcerpt } from '../api/types'
import { PolicyChecks } from './TicketParts'

const refused: PolicyCheck = {
  rule: 'returns_v1',
  order_id: 'ORD-1005',
  allowed: false,
  reason: 'Teslimattan sonraki 14 günlük iade süresi doldu.',
  informational: false,
}

function excerpt(clause_id: string, heading: string): PolicyExcerpt {
  return {
    policy_id: 'returns',
    title: 'İade Politikası',
    version: 1,
    effective_from: '2026-01-01',
    clause_id,
    heading,
    text: `${clause_id} maddesinin metni.`,
  }
}

describe('PolicyChecks', () => {
  it('shows the rule result and the clause the draft cites, with its source', () => {
    render(
      <PolicyChecks
        checks={[refused]}
        excerpts={[excerpt('IADE-3', 'Süresi geçmiş talepler'), excerpt('IADE-2', 'İade süresi')]}
        citedClauseIds={['IADE-3']}
      />,
    )

    expect(screen.getByText('İzin verilmiyor')).toBeInTheDocument()
    const sources = screen.getByRole('heading', { name: 'Dayanağı' }).parentElement!
    expect(within(sources).getByText('İade Politikası v1 · IADE-3')).toBeInTheDocument()
    expect(within(sources).getByText('IADE-3 maddesinin metni.')).toBeInTheDocument()
    // Retrieved but not cited: not presented as the basis of the reply.
    expect(within(sources).queryByText(/IADE-2/)).not.toBeInTheDocument()
  })

  it('labels retrieved clauses as related when the draft cited none', () => {
    render(<PolicyChecks checks={[refused]} excerpts={[excerpt('IADE-2', 'İade süresi')]} />)

    expect(screen.getByRole('heading', { name: 'İlgili politika maddeleri' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Dayanağı' })).not.toBeInTheDocument()
  })

  it('shows sources even without a rule result, and nothing when there is neither', () => {
    const { rerender } = render(
      <PolicyChecks checks={[]} excerpts={[excerpt('IADE-1', 'Kapsam')]} citedClauseIds={['IADE-1']} />,
    )
    expect(screen.getByText('İade Politikası v1 · IADE-1')).toBeInTheDocument()

    rerender(<PolicyChecks checks={[]} />)
    expect(screen.queryByText('Mağaza kuralı')).not.toBeInTheDocument()
  })
})
