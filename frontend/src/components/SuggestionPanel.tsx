import { useState } from 'react'
import { ApiError } from '../api/client'
import { useAnalyze, useRun } from '../api/queries'
import type { AnalysisResult, Run, RunStep, TicketDetail } from '../api/types'
import { CATEGORY_LABEL, PRIORITY_LABEL, timeAgo } from '../lib/format'

const STEP_LABEL: Record<string, string> = {
  load_ticket: 'Read the ticket',
  resolve_orders: "Checked the customer's orders",
  classify: 'Identified the request',
  request_info: 'Noted missing information',
  fetch_context: 'Looked at earlier tickets',
  check_policy: 'Applied store policy',
  plan_action: 'Decided whether to propose an action',
  draft: 'Wrote the reply',
  validate: 'Verified the result',
}

const ERROR_TEXT: Record<string, string> = {
  invalid_output: 'The AI returned something we could not use.',
  llm_rate_limited: 'The AI service is busy (rate limit). Try again in a minute.',
  llm_timeout: 'The AI service did not answer in time.',
  llm_unavailable: 'The AI service is unavailable.',
  token_budget_exceeded: 'The analysis used more than its budget and was stopped.',
  run_timeout: 'The analysis took too long and was stopped.',
  interrupted: 'The server restarted during the analysis.',
}

interface Props {
  ticket: TicketDetail
  runs: Run[]
}

export function SuggestionPanel({ ticket, runs }: Props) {
  const analyze = useAnalyze(ticket.id)
  const latest = runs[0]
  const [watchId, setWatchId] = useState<number | undefined>()
  const isActive = latest && (latest.status === 'queued' || latest.status === 'running')
  const live = useRun(watchId ?? (isActive ? latest.id : undefined))
  const run = live.data && live.data.id === (watchId ?? latest?.id) ? live.data : latest

  function start() {
    analyze.mutate(undefined, { onSuccess: (queued) => setWatchId(queued.id) })
  }

  const inProgress = run && (run.status === 'queued' || run.status === 'running')

  return (
    <section className="carbon" aria-labelledby="suggestion-title">
      <header className="carbon__head">
        <h2 id="suggestion-title">Suggested reply</h2>
        <span className="carbon__tag">Draft by AI</span>
      </header>

      {!run && ticket.status === 'new' ? (
        <div className="carbon__empty">
          <p>
            No suggestion yet. The AI will read the ticket, check the customer's orders and store
            policy, and draft a reply for you to review.
          </p>
          <button
            type="button"
            className="button button--primary"
            onClick={start}
            disabled={analyze.isPending}
          >
            {analyze.isPending ? 'Starting…' : 'Analyze with AI'}
          </button>
        </div>
      ) : null}

      {!run && ticket.status !== 'new' ? (
        <p className="muted">This ticket was handled without an AI suggestion.</p>
      ) : null}

      {analyze.isError ? (
        <p className="notice notice--error" role="alert">
          {analyze.error instanceof ApiError ? analyze.error.message : 'Could not start the analysis.'}
        </p>
      ) : null}

      {inProgress ? <Progress steps={run.steps} /> : null}

      {run?.status === 'failed' ? (
        <div className="notice notice--error" role="alert">
          <strong>The analysis did not finish.</strong>{' '}
          {ERROR_TEXT[run.error_code ?? ''] ?? 'Something went wrong.'}{' '}
          {ticket.status === 'failed'
            ? 'Reopen the ticket to try again, or answer it yourself.'
            : null}
        </div>
      ) : null}

      {run?.status === 'succeeded' && run.result ? (
        <Result key={run.id} run={run} result={run.result} ticketId={ticket.id} />
      ) : null}

      {run && !inProgress ? <HowItWasMade run={run} /> : null}
    </section>
  )
}

function Progress({ steps }: { steps: RunStep[] }) {
  return (
    <div className="progress" role="status" aria-live="polite">
      <p>
        <strong>Analyzing…</strong> <span className="meta">This usually takes a few seconds.</span>
      </p>
      <ol className="progress__steps">
        {steps.map((step) => (
          <li key={step.sequence}>{STEP_LABEL[step.node] ?? step.node}</li>
        ))}
      </ol>
    </div>
  )
}

function Result({ run, result, ticketId }: { run: Run; result: AnalysisResult; ticketId: number }) {
  const analysis = result.analysis
  const [draft, setDraft] = useState(analysis.draft_reply)
  const [copied, setCopied] = useState(false)

  async function copy() {
    await navigator.clipboard.writeText(draft)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="result">
      <dl className="result__facts">
        <div>
          <dt>Request</dt>
          <dd>{CATEGORY_LABEL[analysis.category]}</dd>
        </div>
        <div>
          <dt>Suggested priority</dt>
          <dd>{PRIORITY_LABEL[analysis.suggested_priority]}</dd>
        </div>
        <div>
          <dt>Based on</dt>
          <dd>
            {result.verified_order_ids.length > 0
              ? result.verified_order_ids.join(', ')
              : 'No order data'}
          </dd>
        </div>
      </dl>

      <p className="result__summary">{analysis.summary}</p>

      {analysis.needs_human_review ? (
        <p className="notice notice--warning">
          Check this one carefully: the request is unusual or conflicts with store policy.
        </p>
      ) : null}
      {result.warnings.map((warning) => (
        <p key={warning} className="notice notice--warning">
          {warning}
        </p>
      ))}
      {analysis.missing_information.length > 0 ? (
        <div className="notice">
          <strong>Ask the customer for</strong>
          <ul className="result__missing">
            {analysis.missing_information.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="field">
        <label htmlFor={`draft-${ticketId}`}>Reply to the customer</label>
        <textarea
          id={`draft-${ticketId}`}
          className="textarea"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
      </div>
      <div className="result__actions">
        <button type="button" className="button" onClick={() => void copy()}>
          {copied ? 'Copied' : 'Copy reply'}
        </button>
        {draft !== analysis.draft_reply ? (
          <button type="button" className="button button--quiet" onClick={() => setDraft(analysis.draft_reply)}>
            Restore AI draft
          </button>
        ) : null}
        <span className="meta" role="status">
          {copied ? 'Reply copied to the clipboard.' : `Drafted ${timeAgo(run.finished_at ?? run.created_at)}`}
        </span>
      </div>
    </div>
  )
}

function HowItWasMade({ run }: { run: Run }) {
  return (
    <details className="steps">
      <summary>How this suggestion was made</summary>
      <ol className="steps__list">
        {run.steps.map((step) => (
          <li key={step.sequence} className={step.status === 'error' ? 'is-error' : undefined}>
            <span>{STEP_LABEL[step.node] ?? step.node}</span>
            <span className="meta">{step.duration_ms} ms</span>
            {Array.isArray(step.summary.tool_calls) && step.summary.tool_calls.length > 0 ? (
              <span className="steps__tools meta">
                {(step.summary.tool_calls as { tool: string; found: boolean }[])
                  .map((call) => `${call.tool}${call.found ? '' : ' (nothing found)'}`)
                  .join(', ')}
              </span>
            ) : null}
          </li>
        ))}
      </ol>
      <p className="meta">
        Model {run.model ?? 'unknown'}, prompt {run.prompt_version ?? 'unknown'},{' '}
        {(run.input_tokens ?? 0) + (run.output_tokens ?? 0)} tokens. The AI only classified and
        wrote; order lookups, policy checks and the proposed action come from store rules.
      </p>
    </details>
  )
}
