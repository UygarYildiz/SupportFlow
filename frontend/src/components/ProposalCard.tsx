import { type CSSProperties, useId, useState } from 'react'
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
      {proposal.type === 'create_refund_request' ? (
        <p className="label__strip">
          <span className="tag tag--admin">Yalnızca yönetici</span>
          <span className="meta">İade talepleri yönetici onayı gerektirir.</span>
        </p>
      ) : null}

      <div className="label__body">
        <ProposalChange proposal={proposal} />

        <dl className="label__facts">
          <div>
            <dt>Neden izin veriliyor</dt>
            <dd>{proposal.reason}</dd>
          </div>
          <div>
            <dt>Kural</dt>
            <dd>{proposal.policy_rule}</dd>
          </div>
          {showTicketLink ? (
            <div>
              <dt>Talep</dt>
              <dd>
                <Link to={`/tickets/${proposal.ticket_id}`}>#{proposal.ticket_id} numaralı talebi aç</Link>
              </dd>
            </div>
          ) : null}
        </dl>

        {stamp ? (
          <div
            className={`stamp stamp--${proposal.status}`}
            // Longer words get smaller letters, so every stamp has about the same width.
            style={{ '--stamp-chars': stamp.length } as CSSProperties}
            aria-hidden="true"
          >
            {stamp}
          </div>
        ) : null}
      </div>

      <footer className="label__foot">
        <p className="proposal__status" role="status">
          <strong>{PROPOSAL_STATUS_LABEL[proposal.status]}</strong>
          <span className="meta">
            {pending
              ? ` Son karar tarihi: ${formatDateTime(proposal.expires_at)}`
              : proposal.decided_at
                ? ` ${timeAgo(proposal.decided_at)}`
                : null}
          </span>
        </p>
        {proposal.failure_reason && proposal.status !== 'executed' ? (
          <p className="notice notice--warning">{proposal.failure_reason}</p>
        ) : null}
        {proposal.decision_note ? (
          <p className="meta">Not: {proposal.decision_note}</p>
        ) : null}

        {pending ? (
          proposal.can_decide ? (
            <div className="proposal__decide">
              <div className="field">
                <label htmlFor={noteId}>Denetim kaydı için not (isteğe bağlı)</label>
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
                    ? 'Uygulanıyor…'
                    : 'Onayla ve uygula'}
                </button>
                <button
                  type="button"
                  className="button button--reject"
                  disabled={decide.isPending}
                  onClick={() => submit('reject')}
                >
                  Reddet
                </button>
              </div>
              <p className="meta">Onay, siparişi hemen değiştirir. Bu işlem buradan geri alınamaz.</p>
            </div>
          ) : (
            <p className="notice">
              {proposal.type === 'create_refund_request'
                ? 'İade talepleri hakkında yalnızca yönetici karar verebilir.'
                : 'Rolünüz bu talep hakkında karar veremez.'}
            </p>
          )
        ) : null}

        {decide.isError ? (
          <p className="notice notice--error" role="alert">
            {decide.error instanceof ApiError && decide.error.status === 409
              ? `${decide.error.message}. Güncel durum yukarıda gösteriliyor.`
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
          <dt>Mevcut adres</dt>
          <dd>{payload.current_address ?? 'Kayıtlı değil'}</dd>
        </div>
        <div className="change__row change__row--to">
          <dt>Yeni adres</dt>
          <dd>{payload.new_address}</dd>
        </div>
      </dl>
    )
  }
  return (
    <dl className="change">
      <div className="change__row change__row--to">
        <dt>İade tutarı</dt>
        <dd>{payload.order_total ?? 'Sipariş toplamı'}</dd>
      </div>
      <div className="change__row">
        <dt>Gerekçe</dt>
        <dd>{payload.refund_reason === 'damaged_item' ? 'Ürün hasarlı geldi' : 'İade süresi içinde iade'}</dd>
      </div>
      <p className="meta change__hint">Finans ekibi için bir iade talebi oluşturur. Bu demoda para hareketi olmaz.</p>
    </dl>
  )
}
