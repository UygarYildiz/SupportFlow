import { Link, useParams } from 'react-router'
import { ApiError } from '../api/client'
import { useProposals, useTicket, useTicketRuns, useUpdateTicketStatus } from '../api/queries'
import type { TicketDetail, TicketStatus } from '../api/types'
import { OrderLabel } from '../components/OrderLabel'
import { ProposalCard } from '../components/ProposalCard'
import { SuggestionPanel } from '../components/SuggestionPanel'
import { PolicyChecks, PriorityMark, StatusBadge, Timeline } from '../components/TicketParts'
import { formatDateTime, timeAgo } from '../lib/format'

// Mirrors the manual transitions allowed by the backend (app/domain/ticket_status.py).
const ACTIONS: Partial<Record<TicketStatus, { to: TicketStatus; label: string }[]>> = {
  new: [
    { to: 'resolved', label: 'Çözüldü olarak işaretle' },
    { to: 'needs_info', label: 'Müşteriden bilgi bekleniyor' },
  ],
  awaiting_review: [
    { to: 'resolved', label: 'Çözüldü olarak işaretle' },
    { to: 'needs_info', label: 'Müşteriden bilgi bekleniyor' },
  ],
  needs_info: [{ to: 'new', label: 'Yeniden aç' }],
  failed: [{ to: 'new', label: 'Tekrar denemek için yeniden aç' }],
}

export function TicketPage() {
  const ticketId = Number(useParams().ticketId)
  const ticket = useTicket(ticketId)
  const runs = useTicketRuns(ticketId)
  const proposals = useProposals({ ticketId })

  if (ticket.isPending) return <p className="loading">Talep yükleniyor…</p>
  if (ticket.isError) {
    const missing = ticket.error instanceof ApiError && ticket.error.status === 404
    return (
      <div className="page">
        <p className="notice notice--error" role="alert">
          {missing ? `#${ticketId} numaralı talep bulunamadı.` : `Talep yüklenemedi. ${ticket.error.message}`}
        </p>
        <Link to="/tickets">Taleplere dön</Link>
      </div>
    )
  }

  const data = ticket.data
  const latestRun = runs.data?.[0]
  const checks = latestRun?.status === 'succeeded' ? (latestRun.result?.policy_checks ?? []) : []
  const ticketProposals = proposals.data?.items ?? []
  // Newest first: the open proposal (if any) leads.
  const ordered = [...ticketProposals].sort((a, b) => b.id - a.id)

  return (
    <div className="page page--ticket">
      <header className="ticket-head">
        <Link to="/tickets" className="ticket-head__back">
          Talepler
        </Link>
        <div className="ticket-head__title">
          <h1>{data.subject}</h1>
          <div className="ticket-head__tags">
            <StatusBadge status={data.status} />
            <PriorityMark priority={data.priority} />
            <span className="meta">#{data.id}</span>
          </div>
        </div>
        <StatusActions ticket={data} />
      </header>

      <div className="ticket-grid">
        <div className="ticket-grid__main">
          <section className="message" aria-labelledby="message-title">
            <h2 id="message-title" className="visually-hidden">
              Müşteri mesajı
            </h2>
            <p className="message__from">
              <strong>{data.customer.display_name}</strong>{' '}
              <span className="meta">
                {data.customer.email}, {timeAgo(data.created_at)}
              </span>
            </p>
            <p className="message__body">{data.message}</p>
          </section>

          {runs.isPending ? (
            <p className="loading">Yapay zekâ önerisi yükleniyor…</p>
          ) : (
            <SuggestionPanel ticket={data} runs={runs.data ?? []} />
          )}

          <Timeline events={data.events} />
        </div>

        <aside className="ticket-grid__side" aria-label="Sipariş ve kararlar">
          {ordered.map((proposal) => (
            <ProposalCard key={proposal.id} proposal={proposal} />
          ))}
          {data.order ? (
            <OrderLabel order={data.order} />
          ) : (
            <div className="empty">
              <strong>Bağlı sipariş yok.</strong>
              Müşteri kendi siparişlerinden birine atıf yapmadı.
            </div>
          )}
          <PolicyChecks checks={checks} />
          <p className="meta">Geliş: {formatDateTime(data.created_at)}</p>
        </aside>
      </div>
    </div>
  )
}

function StatusActions({ ticket }: { ticket: TicketDetail }) {
  const update = useUpdateTicketStatus(ticket.id)
  const actions = ACTIONS[ticket.status] ?? []
  if (actions.length === 0) return null
  return (
    <div className="ticket-head__actions">
      {actions.map((action) => (
        <button
          key={action.to}
          type="button"
          className={action.to === 'resolved' ? 'button button--primary' : 'button'}
          disabled={update.isPending}
          onClick={() => update.mutate(action.to)}
        >
          {action.label}
        </button>
      ))}
      {update.isError ? (
        <p className="notice notice--error" role="alert">
          {update.error.message}
        </p>
      ) : null}
    </div>
  )
}
