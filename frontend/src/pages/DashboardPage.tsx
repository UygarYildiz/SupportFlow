import { Link } from 'react-router'
import {
  useProposals,
  useRecentAudit,
  useRecentTickets,
  useTicketSummary,
  useUsers,
} from '../api/queries'
import type { AuditEntry, Proposal, TicketStatus, User } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { StatusBadge } from '../components/TicketParts'
import { ACTION_LABEL, AUDIT_LABEL, STATUS_LABEL, formatDateTime, timeAgo } from '../lib/format'

// Ordered by what needs attention first, as on the ticket list.
const COUNTERS: TicketStatus[] = [
  'awaiting_review',
  'new',
  'needs_info',
  'triaging',
  'failed',
  'resolved',
]
const RECENT = 6

const ROLE_LINE: Record<User['role'], string> = {
  agent_user:
    'Destek uzmanı. Adres değişikliklerini onaylayabilirsiniz; iade talepleri yöneticiye gider.',
  admin: 'Yönetici. Tüm öneriler hakkında karar verebilir ve denetim kaydını görebilirsiniz.',
}

export function DashboardPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const summary = useTicketSummary()
  const proposals = useProposals({ status: 'pending' })

  const pending = (proposals.data?.items ?? []).filter((p) => p.status === 'pending')
  const mine = pending.filter((p) => p.can_decide)
  const others = pending.filter((p) => !p.can_decide)

  return (
    <div className="page">
      <header className="page__head">
        <h1>{user ? `Merhaba, ${user.full_name.split(' ')[0]}` : 'Genel bakış'}</h1>
        {user ? <p className="muted page__lede">{ROLE_LINE[user.role]}</p> : null}
      </header>

      <section aria-labelledby="counts-title">
        <h2 id="counts-title" className="visually-hidden">
          Duruma göre talepler
        </h2>
        {summary.isError ? (
          <p className="notice notice--error" role="alert">
            Talep sayıları yüklenemedi. {summary.error.message}
          </p>
        ) : (
          <ul className="counters">
            {COUNTERS.map((status) => (
              <li key={status}>
                <Link to={`/tickets?status=${status}`} className={`counter counter--${status}`}>
                  <span className="counter__value">
                    {summary.data ? summary.data.by_status[status] : '–'}
                  </span>
                  <span className="counter__label">{STATUS_LABEL[status]}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {proposals.isError ? (
        <p className="notice notice--error" role="alert">
          Öneriler yüklenemedi. {proposals.error.message}
        </p>
      ) : (
        <div className="dash-grid">
          <DecisionList
            id="mine"
            title="Kararınızı bekleyenler"
            items={mine}
            loading={proposals.isPending}
            empty="Şu anda kararınızı bekleyen bir şey yok."
          />
          {isAdmin ? null : (
            <DecisionList
              id="others"
              title="Yönetici bekleyenler"
              hint="İade talepleri yönetici onayı ister. Açıp inceleyebilirsiniz ama karar veremezsiniz."
              items={others}
              loading={proposals.isPending}
              empty="Yönetici bekleyen talep yok."
            />
          )}
          {isAdmin ? <RecentActivity /> : null}
        </div>
      )}

      <div className="dash-grid">
        <RecentTickets />
        {isAdmin ? null : (
          <section className="sheet" aria-labelledby="audit-locked-title">
            <h2 id="audit-locked-title" className="sheet__title">
              Denetim kaydı
            </h2>
            <p className="muted">
              Her değişikliği kimin önerdiğini, onayladığını ya da reddettiğini yalnızca yöneticiler
              görebilir. Verdiğiniz her karar orada kayıt altına alınır.
            </p>
          </section>
        )}
      </div>
    </div>
  )
}

function DecisionList(props: {
  id: string
  title: string
  hint?: string
  items: Proposal[]
  loading: boolean
  empty: string
}) {
  const { id, title, hint, items, loading, empty } = props
  const titleId = `${id}-title`
  return (
    <section className="sheet" aria-labelledby={titleId}>
      <h2 id={titleId} className="sheet__title">
        {title} {loading ? null : <span className="tab__count">{items.length}</span>}
      </h2>
      {hint ? <p className="meta dash-hint">{hint}</p> : null}
      {loading ? <p className="meta">Yükleniyor…</p> : null}
      {!loading && items.length === 0 ? <p className="muted">{empty}</p> : null}
      {items.length > 0 ? (
        <ul className="dash-list">
          {items.map((p) => (
            <li key={p.id} className="dash-list__item">
              <Link to={`/tickets/${p.ticket_id}`} className="dash-list__main">
                {ACTION_LABEL[p.type]}
              </Link>
              <span className="dash-list__ref">{p.order_id}</span>
              {p.type === 'create_refund_request' ? (
                <span className="tag tag--admin">Yalnızca yönetici</span>
              ) : null}
              <span className="meta dash-list__meta">
                Talep #{p.ticket_id}, son karar tarihi {formatDateTime(p.expires_at)}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}

function RecentTickets() {
  const tickets = useRecentTickets(RECENT)
  return (
    <section className="sheet" aria-labelledby="recent-title">
      <h2 id="recent-title" className="sheet__title">
        Son güncellenen talepler
      </h2>
      {tickets.isPending ? <p className="meta">Yükleniyor…</p> : null}
      {tickets.isError ? (
        <p className="notice notice--error" role="alert">
          Talepler yüklenemedi. {tickets.error.message}
        </p>
      ) : null}
      {tickets.data && tickets.data.items.length === 0 ? (
        <p className="muted">Henüz talep yok.</p>
      ) : null}
      {tickets.data && tickets.data.items.length > 0 ? (
        <ul className="dash-list">
          {tickets.data.items.map((t) => (
            <li key={t.id} className="dash-list__item">
              <Link to={`/tickets/${t.id}`} className="dash-list__main">
                {t.subject}
              </Link>
              <StatusBadge status={t.status} />
              <span className="meta dash-list__meta">
                #{t.id}, {t.customer_name}, güncellendi: {timeAgo(t.updated_at)}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      <Link to="/tickets" className="dash-more">
        Tüm talepler
      </Link>
    </section>
  )
}

function RecentActivity() {
  const audit = useRecentAudit(8, true)
  const users = useUsers(true)
  const names = new Map((users.data ?? []).map((u) => [u.id, u.full_name]))

  function actor(entry: AuditEntry): string {
    // Proposals are written by an analysis run; other actor-less entries are system jobs.
    if (entry.actor_id === null) return entry.action === 'proposal.created' ? 'Yapay zekâ analizi' : 'Sistem'
    return names.get(entry.actor_id) ?? `Kullanıcı #${entry.actor_id}`
  }

  return (
    <section className="sheet" aria-labelledby="activity-title">
      <h2 id="activity-title" className="sheet__title">
        Denetim kaydı <span className="tag tag--admin">Yönetici</span>
      </h2>
      {audit.isPending ? <p className="meta">Yükleniyor…</p> : null}
      {audit.isError ? (
        <p className="notice notice--error" role="alert">
          Denetim kaydı yüklenemedi. {audit.error.message}
        </p>
      ) : null}
      {audit.data && audit.data.length === 0 ? (
        <p className="muted">Henüz kayıt yok.</p>
      ) : null}
      {audit.data && audit.data.length > 0 ? (
        <ol className="dash-list">
          {audit.data.map((entry) => {
            const orderId = typeof entry.details.order_id === 'string' ? entry.details.order_id : null
            return (
              <li key={entry.id} className="dash-list__item">
                <span className="dash-list__main">
                  <strong>{actor(entry)}</strong> {AUDIT_LABEL[entry.action] ?? entry.action}
                </span>
                {orderId ? <span className="dash-list__ref">{orderId}</span> : null}
                <span className="meta dash-list__meta">
                  {entry.ticket_id !== null ? (
                    <Link to={`/tickets/${entry.ticket_id}`}>Talep #{entry.ticket_id}</Link>
                  ) : null}{' '}
                  {timeAgo(entry.occurred_at)}
                </span>
              </li>
            )
          })}
        </ol>
      ) : null}
    </section>
  )
}
