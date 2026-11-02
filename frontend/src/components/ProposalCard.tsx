import { useId, useState } from 'react'
import { Link } from 'react-router'
import { ApiError } from '../api/client'
import { useDecide } from '../api/queries'
import type { Decision, Proposal } from '../api/types'
import { ACTION_LABEL, formatDateTime, PROPOSAL_STATUS_LABEL, STAMP_WORD, timeAgo } from '../lib/format'

interface Props {
  proposal: Proposal
  showTicketLink?: boolean
}

/** A proposed order change, laid out like a shipping label. Decisions are stamped onto it. */
export function ProposalCard({ proposal, showTicketLink = false }: Props) {
  const decide = useDecide()
  const [note, setNote] = useState('')
  const noteId = useId()
  const titleId = useId()
  const stamp = STAMP_WORD[proposal.status]
  const pending = proposal.status === 'pending'

  function submit(decision: Decision) {
    decide.mutate({ proposal, decision, note: note.trim() || undefined })
  }

  return (
    <article className={`label proposal proposal--${proposal.status}`} aria-labelledby={titleId}>
      <header className="label__head">
        <h3 id={titleId} className="label__title">
          {ACTION_LABEL[proposal.type]}
        </h3>
        <span className="label__order">{proposal.order_id}</span>
      </header>

      <div className="label__body">
        <ProposalChange proposal={proposal} />

        <dl className="label__facts">
          <div>
            <dt>Why it is allowed</dt>
            <dd>{proposal.reason}</dd>
          </div>
          <div>
            <dt>Rule</dt>
            <dd>{proposal.policy_rule}</dd>
          </div>
          {showTicketLink ? (
            <div>
              <dt>Ticket</dt>
              <dd>
                <Link to={`/tickets/${proposal.ticket_id}`}>Open ticket #{proposal.ticket_id}</Link>
              </dd>
            </div>
          ) : null}
        </dl>

        {stamp ? (
          <div className={`stamp stamp--${proposal.status}`} aria-hidden="true">
            {stamp}
          </div>
        ) : null}
      </div>

      <footer className="label__foot">
        <p className="proposal__status" role="status">
          <strong>{PROPOSAL_STATUS_LABEL[proposal.status]}</strong>
          <span className="meta">
            {pending
              ? ` Decide by ${formatDateTime(proposal.expires_at)}`
              : proposal.decided_at
                ? ` ${timeAgo(proposal.decided_at)}`
                : null}
          </span>
        </p>
        {proposal.failure_reason && proposal.status !== 'executed' ? (
          <p className="notice notice--warning">{proposal.failure_reason}</p>
        ) : null}
        {proposal.decision_note ? (
          <p className="meta">Note: {proposal.decision_note}</p>
        ) : null}

        {pending ? (
          proposal.can_decide ? (
            <div className="proposal__decide">
              <div className="field">
                <label htmlFor={noteId}>Note for the audit log (optional)</label>
                <input
                  id={noteId}
                  className="input"
                  maxLength={500}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  disabled={decide.isPending}
                />
              </div>
              <div className="proposal__buttons">
                <button
                  type="button"
                  className="button button--approve"
                  disabled={decide.isPending}
                  onClick={() => submit('approve')}
                >
                  {decide.isPending && decide.variables?.decision === 'approve'
                    ? 'Applying…'
                    : 'Approve and apply'}
                </button>
                <button
                  type="button"
                  className="button button--reject"
                  disabled={decide.isPending}
                  onClick={() => submit('reject')}
                >
                  Reject
                </button>
              </div>
              <p className="meta">Approving changes the order right away. It cannot be undone here.</p>
            </div>
          ) : (
            <p className="notice">
              {proposal.type === 'create_refund_request'
                ? 'Only an admin can decide refund requests.'
                : 'Your role cannot decide this request.'}
            </p>
          )
        ) : null}

        {decide.isError ? (
          <p className="notice notice--error" role="alert">
            {decide.error instanceof ApiError && decide.error.status === 409
              ? `${decide.error.message}. The latest state is shown above.`
              : decide.error.message}
          </p>
        ) : null}
      </footer>
    </article>
  )
}

function ProposalChange({ proposal }: { proposal: Proposal }) {
  const payload = proposal.payload as Record<string, string | undefined>
  if (proposal.type === 'change_shipping_address') {
    return (
      <dl className="change">
        <div className="change__row change__row--from">
          <dt>Current address</dt>
          <dd>{payload.current_address ?? 'Not recorded'}</dd>
        </div>
        <div className="change__row change__row--to">
          <dt>New address</dt>
          <dd>{payload.new_address}</dd>
        </div>
      </dl>
    )
  }
  return (
    <dl className="change">
      <div className="change__row change__row--to">
        <dt>Refund amount</dt>
        <dd>{payload.order_total ?? 'Order total'}</dd>
      </div>
      <div className="change__row">
        <dt>Reason</dt>
        <dd>{payload.refund_reason === 'damaged_item' ? 'Item arrived damaged' : 'Return within the return window'}</dd>
      </div>
      <p className="meta change__hint">Creates a refund request for finance. No money moves in this demo.</p>
    </dl>
  )
}
