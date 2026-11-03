import { Link, useSearchParams } from 'react-router'
import { PAGE_SIZE, useTicketSummary, useTickets } from '../api/queries'
import type { TicketPriority, TicketStatus } from '../api/types'
import { PriorityMark, StatusBadge } from '../components/TicketParts'
import { CATEGORY_LABEL, PRIORITY_LABEL, STATUS_LABEL, timeAgo } from '../lib/format'

// Ordered by what needs attention first.
const TABS: TicketStatus[] = ['awaiting_review', 'new', 'needs_info', 'failed', 'triaging', 'resolved']

export function TicketsPage() {
  const [params, setParams] = useSearchParams()
  const status = (params.get('status') as TicketStatus | null) ?? undefined
  const priority = (params.get('priority') as TicketPriority | null) ?? undefined
  const offset = Number(params.get('offset') ?? 0)
  const summary = useTicketSummary()
  const tickets = useTickets({ status, priority, offset })

  function update(next: Record<string, string | undefined>) {
    const merged = new URLSearchParams(params)
    for (const [key, value] of Object.entries(next)) {
      if (value) merged.set(key, value)
      else merged.delete(key)
    }
    if (!('offset' in next)) merged.delete('offset')
    setParams(merged)
  }

  const page = tickets.data
  const pending = summary.data?.pending_proposals ?? 0

  return (
    <div className="page">
      <header className="page__head">
        <h1>Talepler</h1>
        {pending > 0 ? (
          <Link to="/approvals" className="attention">
            Karar bekleyen {pending} sipariş değişikliği var
          </Link>
        ) : null}
      </header>

      <div className="filters">
        <nav aria-label="Duruma göre filtrele" className="tabs">
          <button
            type="button"
            className="tab"
            aria-pressed={status === undefined}
            onClick={() => update({ status: undefined })}
          >
            Tümü <span className="tab__count">{summary.data?.total ?? ''}</span>
          </button>
          {TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              className="tab"
              aria-pressed={status === tab}
              onClick={() => update({ status: tab })}
            >
              {STATUS_LABEL[tab]}{' '}
              <span className="tab__count">{summary.data?.by_status[tab] ?? ''}</span>
            </button>
          ))}
        </nav>
        <div className="field field--inline">
          <label htmlFor="priority-filter">Öncelik</label>
          <select
            id="priority-filter"
            className="select"
            value={priority ?? ''}
            onChange={(e) => update({ priority: e.target.value || undefined })}
          >
            <option value="">Hepsi</option>
            {(Object.keys(PRIORITY_LABEL) as TicketPriority[]).map((value) => (
              <option key={value} value={value}>
                {PRIORITY_LABEL[value]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {tickets.isPending ? <p className="loading">Talepler yükleniyor…</p> : null}
      {tickets.isError ? (
        <p className="notice notice--error" role="alert">
          Talepler yüklenemedi. {tickets.error.message}
        </p>
      ) : null}

      {page && page.items.length === 0 ? (
        <div className="empty">
          <strong>Burada talep yok.</strong>
          {status || priority
            ? 'Bu filtrelere uyan talep yok. Başka bir durum seçin ya da öncelik filtresini temizleyin.'
            : 'Yeni müşteri talepleri gelir gelmez burada görünür.'}
        </div>
      ) : null}

      {page && page.items.length > 0 ? (
        <>
          <table className="ticket-table">
            <caption className="visually-hidden">Talepler, en yeni önce</caption>
            <thead>
              <tr>
                <th scope="col">Talep</th>
                <th scope="col">Talep türü</th>
                <th scope="col">Durum</th>
                <th scope="col">Öncelik</th>
                <th scope="col">Geliş</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((ticket) => (
                <tr key={ticket.id}>
                  <td>
                    <Link to={`/tickets/${ticket.id}`} className="ticket-table__subject">
                      {ticket.subject}
                    </Link>
                    <span className="meta ticket-table__who">
                      #{ticket.id}, {ticket.customer_name}
                    </span>
                  </td>
                  <td>{ticket.category ? CATEGORY_LABEL[ticket.category] : <span className="muted">Analiz edilmedi</span>}</td>
                  <td>
                    <StatusBadge status={ticket.status} />
                  </td>
                  <td>
                    <PriorityMark priority={ticket.priority} />
                  </td>
                  <td className="meta">{timeAgo(ticket.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination
            offset={offset}
            total={page.total}
            onChange={(next) => update({ offset: next ? String(next) : undefined })}
          />
        </>
      ) : null}
    </div>
  )
}

function Pagination(props: { offset: number; total: number; onChange: (offset: number) => void }) {
  const { offset, total, onChange } = props
  if (total <= PAGE_SIZE) return null
  const end = Math.min(offset + PAGE_SIZE, total)
  return (
    <nav className="pagination" aria-label="Sayfalar">
      <button
        type="button"
        className="button"
        disabled={offset === 0}
        onClick={() => onChange(Math.max(0, offset - PAGE_SIZE))}
      >
        Önceki
      </button>
      <span className="meta">
        {total} talepten {offset + 1}–{end}
      </span>
      <button
        type="button"
        className="button"
        disabled={end >= total}
        onClick={() => onChange(offset + PAGE_SIZE)}
      >
        Sonraki
      </button>
    </nav>
  )
}
