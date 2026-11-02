import { useCallback, useEffect, useState } from 'react'
import { ApiError, getJson, type HealthResponse, type ReadinessResponse } from './lib/api'

type CheckState =
  | { kind: 'loading' }
  | { kind: 'ok'; detail: string }
  | { kind: 'error'; detail: string }

async function runCheck<T>(path: string, describe: (body: T) => string): Promise<CheckState> {
  try {
    const body = await getJson<T>(path)
    return { kind: 'ok', detail: describe(body) }
  } catch (error) {
    if (error instanceof ApiError && error.status === 503) {
      return { kind: 'error', detail: 'Database unavailable' }
    }
    return { kind: 'error', detail: 'Backend unreachable' }
  }
}

function StatusRow({ label, state }: { label: string; state: CheckState }) {
  const text = state.kind === 'loading' ? 'Checking…' : state.detail
  return (
    <li className={`status status--${state.kind}`}>
      <span className="status__label">{label}</span>
      <span className="status__value" role="status">
        {text}
      </span>
    </li>
  )
}

function loadChecks(): Promise<[CheckState, CheckState]> {
  return Promise.all([
    runCheck<HealthResponse>('/health', () => 'API connected'),
    runCheck<ReadinessResponse>('/ready', (body) => `Database ${body.database}`),
  ])
}

export default function App() {
  const [health, setHealth] = useState<CheckState>({ kind: 'loading' })
  const [ready, setReady] = useState<CheckState>({ kind: 'loading' })

  const applyResults = useCallback(([healthResult, readyResult]: [CheckState, CheckState]) => {
    setHealth(healthResult)
    setReady(readyResult)
  }, [])

  useEffect(() => {
    let cancelled = false
    void loadChecks().then((results) => {
      if (!cancelled) applyResults(results)
    })
    return () => {
      cancelled = true
    }
  }, [applyResults])

  const refresh = () => {
    setHealth({ kind: 'loading' })
    setReady({ kind: 'loading' })
    void loadChecks().then(applyResults)
  }

  return (
    <main className="page">
      <h1>SupportFlow AI</h1>
      <p className="subtitle">Development status</p>
      <ul className="statuses">
        <StatusRow label="API" state={health} />
        <StatusRow label="Database" state={ready} />
      </ul>
      <button type="button" onClick={refresh}>
        Check again
      </button>
    </main>
  )
}
