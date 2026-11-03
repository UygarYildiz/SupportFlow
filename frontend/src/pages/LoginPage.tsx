import { type FormEvent, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/useAuth'

// Seeded demo accounts (scripts/seed_demo.py). Shown only in development or demo mode.
const DEMO_PASSWORD = 'supportflow-demo'
const DEMO_ACCOUNTS = [
  { email: 'selin@novashop.example', label: 'Selin (destek uzmanı)' },
  { email: 'admin@novashop.example', label: 'Ayşe (yönetici)' },
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
      setError(err instanceof ApiError ? err.message : 'Giriş yapılamadı. Tekrar deneyin.')
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
          NovaShop müşterileri için yapay zekânın hazırladığı yanıtları inceleyin ve sipariş değişikliklerini onaylayın.
        </p>
        <form className="login__form" onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="email">İş e-postası</label>
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
            <label htmlFor="password">Parola</label>
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
            {busy ? 'Giriş yapılıyor…' : 'Giriş yap'}
          </button>
        </form>
        {SHOW_DEMO ? (
          <section className="login__demo" aria-labelledby="demo-title">
            <h2 id="demo-title" className="login__demo-title">
              Demo hesapları
            </h2>
            <p className="meta">
              Yalnızca sentetik veri. Selin bir destek uzmanı; Ayşe yönetici ve iadeleri de
              onaylayabilir.
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
                  {account.label} olarak giriş yap
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
  { what: 'Talepleri ve siparişleri görme, yapay zekâ analizi başlatma', agent: true, admin: true },
  { what: 'Adres değişikliğini onaylama', agent: true, admin: true },
  { what: 'İade talebini onaylama', agent: false, admin: true },
  { what: 'Denetim kaydını görme', agent: false, admin: true },
]

/** The right half: what the product does and who may do what. */
function ProductIntro() {
  return (
    <aside className="intro" aria-labelledby="intro-title">
      <h2 id="intro-title" className="intro__title">
        Bir talep SupportFlow'da nasıl ilerler
      </h2>
      <ol className="intro__steps">
        <li className="intro__step">
          <span className="intro__num">1</span>
          <div>
            <strong>Müşteri yazar</strong>
            <p className="muted">“ORD-1003 numaralı siparişimi yeni adresime gönderebilir misiniz?”</p>
          </div>
        </li>
        <li className="intro__step">
          <span className="intro__num">2</span>
          <div className="intro__draft">
            <span className="carbon__tag">Yapay zekâ taslağı</span>
            <strong>Yapay zekâ siparişi ve mağaza kurallarını kontrol eder</strong>
            <p className="muted">
              Bir yanıt taslağı hazırlar ve bir değişiklik önerebilir. Siparişi asla kendisi değiştirmez.
            </p>
          </div>
        </li>
        <li className="intro__step">
          <span className="intro__num">3</span>
          <div className="intro__decide">
            <strong>Kararı bir insan verir</strong>
            <p className="muted">Onay, değişikliği bir kez uygular. Her karar kayıt altına alınır.</p>
            <span className="intro__stamp" aria-hidden="true">
              ONAYLANDI
            </span>
          </div>
        </li>
      </ol>

      <table className="intro__roles">
        <caption>Kim ne yapabilir</caption>
        <thead>
          <tr>
            <th scope="col">
              <span className="visually-hidden">Yetki</span>
            </th>
            <th scope="col">Destek uzmanı</th>
            <th scope="col">Yönetici</th>
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
      <span className="visually-hidden">{value ? 'Evet' : 'Hayır'}</span>
    </td>
  )
}
