import type { PolicyCheck, TicketEvent, TicketPriority, TicketStatus } from '../api/types'
import { ACTION_LABEL, PRIORITY_LABEL, STATUS_LABEL, formatDateTime } from '../lib/format'

export function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`badge badge--${status}`}>{STATUS_LABEL[status]}</span>
}

export function PriorityMark({ priority }: { priority: TicketPriority }) {
  return (
    <span className={`priority priority--${priority}`}>
      <span className="visually-hidden">Priority: </span>
      {PRIORITY_LABEL[priority]}
    </span>
  )
}

export function PolicyChecks({ checks }: { checks: PolicyCheck[] }) {
  if (checks.length === 0) return null
  return (
    <section className="sheet" aria-labelledby="policy-title">
      <h2 id="policy-title" className="sheet__title">
        Store policy
      </h2>
      <ul className="checks">
        {checks.map((check) => {
          const verdict = check.informational ? 'info' : check.allowed ? 'allowed' : 'blocked'
          return (
            <li key={`${check.rule}-${check.order_id}`} className={`check check--${verdict}`}>
              <span className="check__verdict">
                {verdict === 'info' ? 'For information' : verdict === 'allowed' ? 'Allowed' : 'Not allowed'}
              </span>
              <span>{check.reason}</span>
              <span className="meta">
                {check.rule} on {check.order_id}
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

const EVENT_TEXT: Record<string, (p: Record<string, unknown>) => string> = {
  ticket_created: () => 'Ticket received',
  status_changed: (p) => `Status changed to ${STATUS_LABEL[p.to as TicketStatus] ?? String(p.to)}`,
  priority_changed: (p) => `Priority changed to ${PRIORITY_LABEL[p.to as TicketPriority] ?? String(p.to)}`,
  analysis_requested: () => 'AI analysis requested',
  analysis_completed: () => 'AI suggestion ready',
  analysis_failed: () => 'AI analysis failed',
  proposal_created: (p) => `Proposed: ${actionLabel(p.type)}`,
  proposal_approved: (p) => `Approved: ${actionLabel(p.type)}`,
  proposal_rejected: (p) => `Rejected: ${actionLabel(p.type)}`,
  proposal_expired: (p) => `Proposal expired: ${actionLabel(p.type)}`,
  action_executed: (p) => `Applied to the order: ${actionLabel(p.type)}`,
  action_failed: (p) => `Blocked: ${actionLabel(p.type)}${p.reason ? `. ${String(p.reason)}` : ''}`,
}

function actionLabel(type: unknown): string {
  return ACTION_LABEL[type as keyof typeof ACTION_LABEL] ?? String(type)
}

const ACTOR: Record<string, string> = { user: 'Staff', system: 'System', customer: 'Customer' }

export function Timeline({ events }: { events: TicketEvent[] }) {
  return (
    <section className="history" aria-labelledby="history-title">
      <h2 id="history-title" className="section-title">
        History
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
