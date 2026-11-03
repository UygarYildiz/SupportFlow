import type {
  ActionType,
  ProposalStatus,
  TicketCategory,
  TicketPriority,
  TicketStatus,
} from '../api/types'

// Words staff see. Named for what they mean to the user, not how the system stores them.

export const STATUS_LABEL: Record<TicketStatus, string> = {
  new: 'Yeni',
  triaging: 'Analiz ediliyor',
  awaiting_review: 'İncelemeye hazır',
  needs_info: 'Müşteriden bilgi bekleniyor',
  resolved: 'Çözüldü',
  failed: 'Analiz başarısız',
}

export const PRIORITY_LABEL: Record<TicketPriority, string> = {
  low: 'Düşük',
  medium: 'Orta',
  high: 'Yüksek',
  urgent: 'Acil',
}

export const CATEGORY_LABEL: Record<TicketCategory, string> = {
  delivery_delay: 'Teslimat sorusu',
  refund_request: 'İade talebi',
  address_change: 'Adres değişikliği',
  damaged_item: 'Hasarlı ürün',
  general: 'Genel soru',
  unknown: 'Belirsiz talep',
}

export const ACTION_LABEL: Record<ActionType, string> = {
  change_shipping_address: 'Teslimat adresini değiştir',
  create_refund_request: 'İade talebi oluştur',
}

export const PROPOSAL_STATUS_LABEL: Record<ProposalStatus, string> = {
  pending: 'Karar bekliyor',
  approved: 'Onaylandı',
  executing: 'Uygulanıyor',
  executed: 'Uygulandı',
  rejected: 'Reddedildi',
  failed: 'Engellendi',
  expired: 'Süresi doldu',
}

/** Audit actions as a sentence predicate: "<actor> bir değişikliği onayladı". */
export const AUDIT_LABEL: Record<string, string> = {
  'proposal.created': 'bir değişiklik önerdi',
  'proposal.approved': 'bir değişikliği onayladı',
  'proposal.rejected': 'bir değişikliği reddetti',
  'proposal.expired': 'bir önerinin süresini doldurdu',
  'proposal.integrity_failed': 'değiştirilmiş bir öneriyle karşılaştı',
  'action.executed': 'siparişe değişikliği uyguladı',
  'action.failed': 'değişikliği uygularken engellendi',
}

/** Word printed by the decision stamp. Rubber-stamp lettering is uppercase by nature. */
export const STAMP_WORD: Partial<Record<ProposalStatus, string>> = {
  executed: 'ONAYLANDI',
  rejected: 'REDDEDİLDİ',
  failed: 'ENGELLENDİ',
  expired: 'SÜRESİ DOLDU',
}

const RELATIVE = new Intl.RelativeTimeFormat('tr', { numeric: 'auto' })
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
  return 'az önce'
}

const DATE_TIME = new Intl.DateTimeFormat('tr', {
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
})
const DATE = new Intl.DateTimeFormat('tr', { day: 'numeric', month: 'short', year: 'numeric' })

export const formatDateTime = (iso: string) => DATE_TIME.format(new Date(iso))
export const formatDate = (iso: string) => DATE.format(new Date(iso))
