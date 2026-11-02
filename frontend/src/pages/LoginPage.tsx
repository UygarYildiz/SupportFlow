import { type FormEvent, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'

// Seeded demo accounts (scripts/seed_demo.py). Shown only in development or demo mode.
const DEMO_PASSWORD = 'supportflow-demo'
const DEMO_ACCOUNTS = [
  { email: 'sam@novashop.example', label: 'Sam, support agent' },
  { email: 'admin@novashop.example', label: 'Ada, admin' },
]
const SHOW_DEMO = import.meta.env.DEV || import.meta.env.VITE_DEMO_MODE === 'true'

export function LoginPage() {
  const { user, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const next = (location.state as { from?: string } | null)?.from ?? '/tickets'

  if (user) return <Navigate to={next} replace />

  async function submit(emailValue: string, passwordValue: string) {
    setBusy(true)
    setError(null)
    try {
      await signIn(emailValue, passwordValue)
      navigate(next, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Sign-in failed. Try again.')
    } finally {
      setBusy(false)
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    void submit(email, password)
  }

  return (
    <div className="login">
      <div className="login__panel">
        <div className="wordmark wordmark--large">SupportFlow</div>
        <p className="login__intro">
          Review AI-drafted replies and approve order changes for NovaShop customers.
        </p>
        <form className="login__form" onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="email">Work email</label>
            <input
              id="email"
              className="input"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              className="input"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error ? (
            <p className="notice notice--error" role="alert">
              {error}
            </p>
          ) : null}
          <button className="button button--primary" type="submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        {SHOW_DEMO ? (
          <section className="login__demo" aria-labelledby="demo-title">
            <h2 id="demo-title" className="login__demo-title">
              Demo accounts
            </h2>
            <p className="meta">Synthetic data only. Each role sees different approval rights.</p>
            <div className="login__demo-buttons">
              {DEMO_ACCOUNTS.map((account) => (
                <button
                  key={account.email}
                  type="button"
                  className="button"
                  disabled={busy}
                  onClick={() => void submit(account.email, DEMO_PASSWORD)}
                >
                  Sign in as {account.label}
                </button>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  )
}
