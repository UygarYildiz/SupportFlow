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
        <h1>Onaylar</h1>
        <p className="muted page__lede">
          Yapay zekânın önerdiği sipariş değişiklikleri. Biri onaylamadıkça siparişe hiçbir şey olmaz.
        </p>
      </header>

      <nav className="tabs" aria-label="Onay görünümü">
        <button
          type="button"
          className="tab"
          aria-pressed={view === 'pending'}
          onClick={() => setParams({})}
        >
          Karar bekleyenler
        </button>
        <button
          type="button"
          className="tab"
          aria-pressed={view === 'decided'}
          onClick={() => setParams({ view: 'decided' })}
        >
          Karar verilenler
        </button>
      </nav>

      {proposals.isPending ? <p className="loading">Öneriler yükleniyor…</p> : null}
      {proposals.isError ? (
        <p className="notice notice--error" role="alert">
          Öneriler yüklenemedi. {proposals.error.message}
        </p>
      ) : null}

      {proposals.data && items.length === 0 ? (
        <div className="empty">
          <strong>{view === 'pending' ? 'Sizi bekleyen bir şey yok.' : 'Henüz karar verilmedi.'}</strong>
          {view === 'pending'
            ? 'Bir yapay zekâ analizi adres değişikliği ya da iade önerdiğinde burada görünür.'
            : 'Onaylanan, reddedilen ve engellenen öneriler burada görünür.'}
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
