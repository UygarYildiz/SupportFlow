import { useSearchParams } from 'react-router'
import { useProposals } from '../api/queries'
import { ProposalCard } from '../components/ProposalCard'

export function ApprovalsPage() {
  const [params, setParams] = useSearchParams()
  const view = params.get('view') === 'decided' ? 'decided' : 'pending'
  const proposals = useProposals(view === 'pending' ? { status: 'pending' } : {})
  const items = (proposals.data?.items ?? [])
    .filter((p) => (view === 'pending' ? p.status === 'pending' : p.status !== 'pending'))
    .sort((a, b) => (view === 'pending' ? a.id - b.id : b.id - a.id))

  return (
    <div className="page">
      <header className="page__head">
        <h1>Approvals</h1>
        <p className="muted page__lede">
          Order changes proposed by the AI. Nothing happens to an order until someone approves it.
        </p>
      </header>

      <nav className="tabs" aria-label="Approval view">
        <button
          type="button"
          className="tab"
          aria-pressed={view === 'pending'}
          onClick={() => setParams({})}
        >
          Waiting for a decision
        </button>
        <button
          type="button"
          className="tab"
          aria-pressed={view === 'decided'}
          onClick={() => setParams({ view: 'decided' })}
        >
          Decided
        </button>
      </nav>

      {proposals.isPending ? <p className="loading">Loading proposals…</p> : null}
      {proposals.isError ? (
        <p className="notice notice--error" role="alert">
          Could not load proposals. {proposals.error.message}
        </p>
      ) : null}

      {proposals.data && items.length === 0 ? (
        <div className="empty">
          <strong>{view === 'pending' ? 'Nothing is waiting for you.' : 'No decisions yet.'}</strong>
          {view === 'pending'
            ? 'When an AI analysis proposes an address change or a refund, it appears here.'
            : 'Approved, rejected and blocked proposals appear here.'}
        </div>
      ) : null}

      <div className="label-board">
        {items.map((proposal) => (
          <ProposalCard key={proposal.id} proposal={proposal} showTicketLink />
        ))}
      </div>
    </div>
  )
}
