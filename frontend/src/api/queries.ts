import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { request } from './client'
import type {
  AuditEntry,
  Decision,
  Page,
  Proposal,
  ProposalStatus,
  Run,
  Ticket,
  TicketDetail,
  TicketPriority,
  TicketStatus,
  TicketSummary,
  User,
} from './types'

export const keys = {
  me: ['me'] as const,
  summary: ['tickets', 'summary'] as const,
  tickets: (filters: TicketFilters) => ['tickets', 'list', filters] as const,
  ticket: (id: number) => ['tickets', 'detail', id] as const,
  runs: (ticketId: number) => ['tickets', 'runs', ticketId] as const,
  run: (id: number) => ['runs', id] as const,
  proposals: (filters: ProposalFilters) => ['proposals', filters] as const,
  audit: (ticketId: number) => ['audit', ticketId] as const,
}

export interface TicketFilters {
  status?: TicketStatus
  priority?: TicketPriority
  offset?: number
}

export interface ProposalFilters {
  status?: ProposalStatus
  ticketId?: number
}

export const PAGE_SIZE = 25
const TERMINAL_RUN = new Set(['succeeded', 'failed'])

export function useMe(enabled: boolean) {
  return useQuery({
    queryKey: keys.me,
    queryFn: () => request<User>('GET', '/auth/me'),
    enabled,
    staleTime: 5 * 60_000,
  })
}

export function useTicketSummary() {
  return useQuery({
    queryKey: keys.summary,
    queryFn: () => request<TicketSummary>('GET', '/tickets/summary'),
  })
}

export function useTickets(filters: TicketFilters) {
  return useQuery({
    queryKey: keys.tickets(filters),
    queryFn: () =>
      request<Page<Ticket>>('GET', '/tickets', {
        query: { ...filters, limit: PAGE_SIZE },
      }),
    placeholderData: (previous) => previous,
  })
}

export function useTicket(id: number) {
  return useQuery({
    queryKey: keys.ticket(id),
    queryFn: () => request<TicketDetail>('GET', `/tickets/${id}`),
  })
}

export function useTicketRuns(ticketId: number) {
  return useQuery({
    queryKey: keys.runs(ticketId),
    queryFn: () => request<Run[]>('GET', `/tickets/${ticketId}/runs`),
  })
}

/** Polls a run until it finishes, then refreshes everything the run may have changed. */
export function useRun(id: number | undefined) {
  const client = useQueryClient()
  return useQuery({
    queryKey: keys.run(id ?? 0),
    queryFn: async () => {
      const run = await request<Run>('GET', `/runs/${id}`)
      if (TERMINAL_RUN.has(run.status)) {
        await Promise.all([
          client.invalidateQueries({ queryKey: ['tickets'] }),
          client.invalidateQueries({ queryKey: ['proposals'] }),
        ])
      }
      return run
    },
    enabled: id !== undefined,
    refetchInterval: (query) =>
      query.state.data && TERMINAL_RUN.has(query.state.data.status) ? false : 800,
  })
}

export function useAnalyze(ticketId: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: () => request<Run>('POST', `/tickets/${ticketId}/analyze`),
    onSuccess: () => client.invalidateQueries({ queryKey: ['tickets'] }),
  })
}

export function useUpdateTicketStatus(ticketId: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (status: TicketStatus) =>
      request<TicketDetail>('PATCH', `/tickets/${ticketId}`, { body: { status } }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['tickets'] }),
  })
}

export function useProposals(filters: ProposalFilters) {
  return useQuery({
    queryKey: keys.proposals(filters),
    queryFn: () =>
      request<Page<Proposal>>('GET', '/proposals', {
        query: { status: filters.status, ticket_id: filters.ticketId, limit: 100 },
      }),
  })
}

export function useDecide() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: { proposal: Proposal; decision: Decision; note?: string }) =>
      request<Proposal>('POST', `/proposals/${input.proposal.id}/decision`, {
        body: {
          decision: input.decision,
          expected_version: input.proposal.version,
          note: input.note || null,
        },
      }),
    // Refetch on success and on failure: a 409 means our copy is stale.
    onSettled: () =>
      Promise.all([
        client.invalidateQueries({ queryKey: ['proposals'] }),
        client.invalidateQueries({ queryKey: ['tickets'] }),
        client.invalidateQueries({ queryKey: ['audit'] }),
      ]),
  })
}

export function useAudit(ticketId: number, enabled: boolean) {
  return useQuery({
    queryKey: keys.audit(ticketId),
    queryFn: () =>
      request<AuditEntry[]>('GET', '/audit', { query: { ticket_id: ticketId, limit: 200 } }),
    enabled,
  })
}
