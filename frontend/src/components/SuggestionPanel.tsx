import { useState } from 'react'
import { ApiError } from '../api/client'
import { useAnalyze, useRun } from '../api/queries'
import type { AnalysisResult, Run, RunStep, TicketDetail } from '../api/types'
import { CATEGORY_LABEL, PRIORITY_LABEL, timeAgo } from '../lib/format'

const STEP_LABEL: Record<string, string> = {
  load_ticket: 'Talebi okudu',
  resolve_orders: 'Müşterinin siparişlerini kontrol etti',
  classify: 'Talebin türünü belirledi',
  request_info: 'Eksik bilgiyi not etti',
  fetch_context: 'Önceki taleplere baktı',
  check_policy: 'Mağaza kuralını uyguladı',
  plan_action: 'Aksiyon önerilip önerilmeyeceğine karar verdi',
  retrieve_policy: 'Politika maddelerini aradı',
  draft: 'Yanıtı yazdı',
  validate: 'Sonucu doğruladı',
}

const ERROR_TEXT: Record<string, string> = {
  invalid_output: 'Yapay zekâ kullanılamayan bir yanıt döndürdü.',
  llm_rate_limited: 'Yapay zekâ servisi meşgul (istek sınırı). Bir dakika sonra tekrar deneyin.',
  llm_timeout: 'Yapay zekâ servisi zamanında yanıt vermedi.',
  llm_unavailable: 'Yapay zekâ servisine ulaşılamıyor.',
  token_budget_exceeded: 'Analiz bütçesini aştığı için durduruldu.',
  run_timeout: 'Analiz çok uzun sürdüğü için durduruldu.',
  interrupted: 'Analiz sırasında sunucu yeniden başladı.',
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
        <h2 id="suggestion-title">Önerilen yanıt</h2>
        <span className="carbon__tag">Yapay zekâ taslağı</span>
      </header>

      {!run && ticket.status === 'new' ? (
        <div className="carbon__empty">
          <p>
            Henüz öneri yok. Yapay zekâ talebi okuyacak, müşterinin siparişlerini ve mağaza
            kurallarını kontrol edecek ve incelemeniz için bir yanıt taslağı hazırlayacak.
          </p>
          <button
            type="button"
            className="button button--primary"
            onClick={start}
            disabled={analyze.isPending}
          >
            {analyze.isPending ? 'Başlatılıyor…' : 'Yapay zekâ ile analiz et'}
          </button>
        </div>
      ) : null}

      {!run && ticket.status !== 'new' ? (
        <p className="muted">Bu talep yapay zekâ önerisi olmadan ele alındı.</p>
      ) : null}

      {analyze.isError ? (
        <p className="notice notice--error" role="alert">
          {analyze.error instanceof ApiError ? analyze.error.message : 'Analiz başlatılamadı.'}
        </p>
      ) : null}

      {inProgress ? <Progress steps={run.steps} /> : null}

      {run?.status === 'failed' ? (
        <div className="notice notice--error" role="alert">
          <strong>Analiz tamamlanamadı.</strong>{' '}
          {ERROR_TEXT[run.error_code ?? ''] ?? 'Bir şeyler ters gitti.'}{' '}
          {ticket.status === 'failed'
            ? 'Tekrar denemek için talebi yeniden açın ya da kendiniz yanıtlayın.'
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
        <strong>Analiz ediliyor…</strong> <span className="meta">Bu genellikle birkaç saniye sürer.</span>
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
          <dt>Talep türü</dt>
          <dd>{CATEGORY_LABEL[analysis.category]}</dd>
        </div>
        <div>
          <dt>Önerilen öncelik</dt>
          <dd>{PRIORITY_LABEL[analysis.suggested_priority]}</dd>
        </div>
        <div>
          <dt>Dayanağı</dt>
          <dd>
            {result.verified_order_ids.length > 0
              ? result.verified_order_ids.join(', ')
              : 'Sipariş verisi yok'}
          </dd>
        </div>
      </dl>

      <p className="result__summary">{analysis.summary}</p>

      {analysis.needs_human_review ? (
        <p className="notice notice--warning">
          Bunu dikkatle inceleyin: talep olağan dışı ya da mağaza kurallarıyla çelişiyor.
        </p>
      ) : null}
      {result.warnings.map((warning) => (
        <p key={warning} className="notice notice--warning">
          {warning}
        </p>
      ))}
      {analysis.missing_information.length > 0 ? (
        <div className="notice">
          <strong>Müşteriden istenecekler</strong>
          <ul className="result__missing">
            {analysis.missing_information.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="field">
        <label htmlFor={`draft-${ticketId}`}>Müşteriye yanıt</label>
        <textarea
          id={`draft-${ticketId}`}
          className="textarea"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
      </div>
      <div className="result__actions">
        <button type="button" className="button" onClick={() => void copy()}>
          {copied ? 'Kopyalandı' : 'Yanıtı kopyala'}
        </button>
        {draft !== analysis.draft_reply ? (
          <button type="button" className="button button--quiet" onClick={() => setDraft(analysis.draft_reply)}>
            Yapay zekâ taslağına dön
          </button>
        ) : null}
        <span className="meta" role="status">
          {copied ? 'Yanıt panoya kopyalandı.' : `Taslak hazırlandı: ${timeAgo(run.finished_at ?? run.created_at)}`}
        </span>
      </div>
    </div>
  )
}

function HowItWasMade({ run }: { run: Run }) {
  return (
    <details className="steps">
      <summary>Bu öneri nasıl hazırlandı</summary>
      <ol className="steps__list">
        {run.steps.map((step) => (
          <li key={step.sequence} className={step.status === 'error' ? 'is-error' : undefined}>
            <span>{STEP_LABEL[step.node] ?? step.node}</span>
            <span className="meta">{step.duration_ms} ms</span>
            {Array.isArray(step.summary.tool_calls) && step.summary.tool_calls.length > 0 ? (
              <span className="steps__tools meta">
                {(step.summary.tool_calls as { tool: string; found: boolean }[])
                  .map((call) => `${call.tool}${call.found ? '' : ' (bulunamadı)'}`)
                  .join(', ')}
              </span>
            ) : null}
          </li>
        ))}
      </ol>
      <p className="meta">
        Model {run.model ?? 'bilinmiyor'}, prompt {run.prompt_version ?? 'bilinmiyor'},{' '}
        {(run.input_tokens ?? 0) + (run.output_tokens ?? 0)} token. Yapay zekâ yalnızca sınıflandırdı ve
        metni yazdı; sipariş sorguları, kural kontrolleri ve önerilen aksiyon mağaza kurallarından gelir.
      </p>
    </details>
  )
}
