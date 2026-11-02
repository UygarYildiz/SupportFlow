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
  const next = (location.state as { from?: string } | null)?.from ?? '/'

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
            <p className="meta">
              Synthetic data only. Sam is a support agent; Ada is an admin and can also approve
              refunds.
            </p>
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
      <ProductIntro />
    </div>
  )
}

const PERMISSIONS: { what: string; agent: boolean; admin: boolean }[] = [
  { what: 'Read tickets and orders, run AI analysis', agent: true, admin: true },
  { what: 'Approve an address change', agent: true, admin: true },
  { what: 'Approve a refund request', agent: false, admin: true },
  { what: 'See the audit trail', agent: false, admin: true },
]

/** The right half: what the product does and who may do what. */
function ProductIntro() {
  return (
    <aside className="intro" aria-labelledby="intro-title">
      <h2 id="intro-title" className="intro__title">
        How a request moves through SupportFlow
      </h2>
      <ol className="intro__steps">
        <li className="intro__step">
          <span className="intro__num">1</span>
          <div>
            <strong>A customer writes in</strong>
            <p className="muted">“Please send ORD-1003 to my new address.”</p>
          </div>
        </li>
        <li className="intro__step">
          <span className="intro__num">2</span>
          <div className="intro__draft">
            <span className="carbon__tag">Draft by AI</span>
            <strong>The AI checks the order and store policy</strong>
            <p className="muted">
              It drafts a reply and may propose a change. It never changes an order itself.
            </p>
          </div>
        </li>
        <li className="intro__step">
          <span className="intro__num">3</span>
          <div className="intro__decide">
            <strong>A person decides</strong>
            <p className="muted">Approving applies the change once. Every decision is recorded.</p>
            <span className="intro__stamp" aria-hidden="true">
              APPROVED
            </span>
          </div>
        </li>
      </ol>

      <table className="intro__roles">
        <caption>Who can do what</caption>
        <thead>
          <tr>
            <th scope="col">
              <span className="visually-hidden">Permission</span>
            </th>
            <th scope="col">Support agent</th>
            <th scope="col">Admin</th>
          </tr>
        </thead>
        <tbody>
          {PERMISSIONS.map((row) => (
            <tr key={row.what}>
              <th scope="row">{row.what}</th>
              <Allowed value={row.agent} />
              <Allowed value={row.admin} />
            </tr>
          ))}
        </tbody>
      </table>
    </aside>
  )
}

function Allowed({ value }: { value: boolean }) {
  return (
    <td className={value ? 'yes' : 'no'}>
      <span aria-hidden="true">{value ? '✓' : '–'}</span>
      <span className="visually-hidden">{value ? 'Yes' : 'No'}</span>
    </td>
  )
}
