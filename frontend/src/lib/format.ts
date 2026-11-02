import type {
  ActionType,
  ProposalStatus,
  TicketCategory,
  TicketPriority,
  TicketStatus,
} from '../api/types'

// Words staff see. Named for what they mean to the user, not how the system stores them.

export const STATUS_LABEL: Record<TicketStatus, string> = {
  new: 'New',
  triaging: 'Analyzing',
  awaiting_review: 'Ready for review',
  needs_info: 'Waiting on customer',
  resolved: 'Resolved',
  failed: 'Analysis failed',
}

export const PRIORITY_LABEL: Record<TicketPriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  urgent: 'Urgent',
}

export const CATEGORY_LABEL: Record<TicketCategory, string> = {
  delivery_delay: 'Delivery question',
  refund_request: 'Refund request',
  address_change: 'Address change',
  damaged_item: 'Damaged item',
  general: 'General question',
  unknown: 'Unclear request',
}

export const ACTION_LABEL: Record<ActionType, string> = {
  change_shipping_address: 'Change delivery address',
  create_refund_request: 'Create refund request',
}

export const PROPOSAL_STATUS_LABEL: Record<ProposalStatus, string> = {
  pending: 'Waiting for a decision',
  approved: 'Approved',
  executing: 'Applying',
  executed: 'Applied',
  rejected: 'Rejected',
  failed: 'Blocked',
  expired: 'Expired',
}

/** Audit actions as a sentence predicate: "<actor> approved a change". */
export const AUDIT_LABEL: Record<string, string> = {
  'proposal.created': 'proposed a change',
  'proposal.approved': 'approved a change',
  'proposal.rejected': 'rejected a change',
  'proposal.expired': 'let a proposal expire',
  'proposal.integrity_failed': 'hit a changed proposal',
  'action.executed': 'applied a change to',
  'action.failed': 'was blocked applying a change to',
}

/** Word printed by the decision stamp. Rubber-stamp lettering is uppercase by nature. */
export const STAMP_WORD: Partial<Record<ProposalStatus, string>> = {
  executed: 'APPROVED',
  rejected: 'REJECTED',
  failed: 'BLOCKED',
  expired: 'EXPIRED',
}

const RELATIVE = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
const STEPS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 365 * 24 * 3600],
  ['month', 30 * 24 * 3600],
  ['week', 7 * 24 * 3600],
  ['day', 24 * 3600],
  ['hour', 3600],
  ['minute', 60],
]

export function timeAgo(iso: string, now: Date = new Date()): string {
  const seconds = (new Date(iso).getTime() - now.getTime()) / 1000
  for (const [unit, size] of STEPS) {
    if (Math.abs(seconds) >= size) return RELATIVE.format(Math.round(seconds / size), unit)
  }
  return 'just now'
}

const DATE_TIME = new Intl.DateTimeFormat('en', {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
})
const DATE = new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric' })

export const formatDateTime = (iso: string) => DATE_TIME.format(new Date(iso))
export const formatDate = (iso: string) => DATE.format(new Date(iso))
