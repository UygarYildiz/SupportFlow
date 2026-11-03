// Readable aliases over the generated OpenAPI types (npm run gen:api).
import type { components } from './schema'

type S = components['schemas']

export type User = S['UserOut']
export type Ticket = S['TicketOut']
export type TicketDetail = S['TicketDetail']
export type TicketEvent = S['TicketEventOut']
export type TicketSummary = S['TicketSummary']
export type TicketStatus = S['TicketStatus']
export type TicketPriority = S['TicketPriority']
export type TicketCategory = S['TicketCategory']
export type Order = S['OrderOut']
export type Run = S['RunOut']
export type RunStep = S['RunStepOut']
export type AnalysisResult = S['AnalysisResult']
export type PolicyCheck = S['PolicyCheck']
export type PolicyExcerpt = S['PolicyExcerptFact']
export type Proposal = S['ProposalOut']
export type ProposalStatus = S['ProposalStatus']
export type ActionType = S['ActionType']
export type Decision = S['Decision']
export type AuditEntry = S['AuditLogOut']

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}
