import type { PolicyCheck, TicketEvent, TicketPriority, TicketStatus } from '../api/types'
import { ACTION_LABEL, PRIORITY_LABEL, STATUS_LABEL, formatDateTime } from '../lib/format'

export function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`badge badge--${status}`}>{STATUS_LABEL[status]}</span>
}

export function PriorityMark({ priority }: { priority: TicketPriority }) {
  return (
    <span className={`priority priority--${priority}`}>
      <span className="visually-hidden">Öncelik: </span>
      {PRIORITY_LABEL[priority]}
    </span>
  )
}

export function PolicyChecks({ checks }: { checks: PolicyCheck[] }) {
  if (checks.length === 0) return null
  return (
    <section className="sheet" aria-labelledby="policy-title">
      <h2 id="policy-title" className="sheet__title">
        Mağaza kuralı
      </h2>
      <ul className="checks">
        {checks.map((check) => {
          const verdict = check.informational ? 'info' : check.allowed ? 'allowed' : 'blocked'
          return (
            <li key={`${check.rule}-${check.order_id}`} className={`check check--${verdict}`}>
              <span className="check__verdict">
                {verdict === 'info' ? 'Bilgi amaçlı' : verdict === 'allowed' ? 'İzin veriliyor' : 'İzin verilmiyor'}
              </span>
              <span>{check.reason}</span>
              <span className="meta">
                {check.order_id} · {check.rule}
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

const EVENT_TEXT: Record<string, (p: Record<string, unknown>) => string> = {
  ticket_created: () => 'Talep alındı',
  status_changed: (p) => `Durum değişti: ${STATUS_LABEL[p.to as TicketStatus] ?? String(p.to)}`,
  priority_changed: (p) => `Öncelik değişti: ${PRIORITY_LABEL[p.to as TicketPriority] ?? String(p.to)}`,
  analysis_requested: () => 'Yapay zekâ analizi istendi',
  analysis_completed: () => 'Yapay zekâ önerisi hazır',
  analysis_failed: () => 'Yapay zekâ analizi başarısız',
  proposal_created: (p) => `Önerildi: ${actionLabel(p.type)}`,
  proposal_approved: (p) => `Onaylandı: ${actionLabel(p.type)}`,
  proposal_rejected: (p) => `Reddedildi: ${actionLabel(p.type)}`,
  proposal_expired: (p) => `Önerinin süresi doldu: ${actionLabel(p.type)}`,
  action_executed: (p) => `Siparişe uygulandı: ${actionLabel(p.type)}`,
  action_failed: (p) => `Engellendi: ${actionLabel(p.type)}${p.reason ? `. ${String(p.reason)}` : ''}`,
}

function actionLabel(type: unknown): string {
  return ACTION_LABEL[type as keyof typeof ACTION_LABEL] ?? String(type)
}

const ACTOR: Record<string, string> = { user: 'Personel', system: 'Sistem', customer: 'Müşteri' }

export function Timeline({ events }: { events: TicketEvent[] }) {
  return (
    <section className="history" aria-labelledby="history-title">
      <h2 id="history-title" className="section-title">
        Geçmiş
      </h2>
      <ol className="timeline">
        {events.map((event) => (
          <li key={event.id} className={`timeline__item timeline__item--${event.actor_type}`}>
            <span>{EVENT_TEXT[event.event_type]?.(event.payload) ?? event.event_type}</span>
            <span className="meta">
              {ACTOR[event.actor_type]}, {formatDateTime(event.occurred_at)}
            </span>
          </li>
        ))}
      </ol>
    </section>
  )
}
