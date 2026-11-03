import { type FormEvent, useState } from 'react'
import { ApiError } from '../api/client'
import { useChangePassword } from '../api/queries'
import { useAuth } from '../auth/useAuth'

const MIN_PASSWORD = 12
// Field names match the API body, so the request is built without re-mapping values.
const EMPTY = { current_password: '', new_password: '', repeated: '' }

/** The signed-in user's own account: details and password change. */
export function AccountPage() {
  const { user } = useAuth()
  const change = useChangePassword()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    setDone(false)
    if (form.new_password !== form.repeated) {
      setError('Yeni parolalar birbirini tutmuyor.')
      return
    }
    setError(null)
    const { current_password, new_password } = form
    change.mutate(
      { current_password, new_password },
      {
        onSuccess: () => {
          setDone(true)
          setForm(EMPTY)
        },
        onError: (err) => setError(err instanceof ApiError ? err.message : 'Parola değiştirilemedi.'),
      },
    )
  }

  return (
    <div className="page">
      <header className="page__head">
        <h1>Hesabım</h1>
        {user ? (
          <p className="muted page__lede">
            {user.full_name} · {user.email} · {user.role === 'admin' ? 'Yönetici' : 'Destek uzmanı'}
          </p>
        ) : null}
      </header>

      <form className="sheet account__form" onSubmit={onSubmit} aria-labelledby="password-title">
        <h2 id="password-title" className="sheet__title">
          Parolayı değiştir
        </h2>
        <div className="field">
          <label htmlFor="current-password">Mevcut parola</label>
          <input
            id="current-password"
            className="input"
            type="password"
            required
            autoComplete="current-password"
            value={form.current_password}
            onChange={(e) => setForm({ ...form, current_password: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="new-password">Yeni parola</label>
          <input
            id="new-password"
            className="input"
            type="password"
            required
            minLength={MIN_PASSWORD}
            autoComplete="new-password"
            value={form.new_password}
            onChange={(e) => setForm({ ...form, new_password: e.target.value })}
          />
          <span className="meta">En az {MIN_PASSWORD} karakter.</span>
        </div>
        <div className="field">
          <label htmlFor="new-password-again">Yeni parola (tekrar)</label>
          <input
            id="new-password-again"
            className="input"
            type="password"
            required
            autoComplete="new-password"
            value={form.repeated}
            onChange={(e) => setForm({ ...form, repeated: e.target.value })}
          />
        </div>
        {error ? (
          <p className="notice notice--error" role="alert">
            {error}
          </p>
        ) : null}
        {done ? (
          <p className="notice notice--success" role="status">
            Parolanız değişti. Bir sonraki girişte yenisini kullanın.
          </p>
        ) : null}
        <div>
          <button className="button button--primary" type="submit" disabled={change.isPending}>
            {change.isPending ? 'Kaydediliyor…' : 'Parolayı değiştir'}
          </button>
        </div>
      </form>
    </div>
  )
}
