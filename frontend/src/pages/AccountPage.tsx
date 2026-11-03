import { type FormEvent, useState } from 'react'
import { ApiError } from '../api/client'
import { useChangePassword } from '../api/queries'
import { useAuth } from '../auth/useAuth'

const MIN_PASSWORD = 12

/** The signed-in user's own account: details and password change. */
export function AccountPage() {
  const { user } = useAuth()
  const change = useChangePassword()
  const [form, setForm] = useState({ current: '', next: '', again: '' })
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    setDone(false)
    if (form.next !== form.again) {
      setError('Yeni parolalar birbirini tutmuyor.')
      return
    }
    setError(null)
    change.mutate(
      { current_password: form.current, new_password: form.next },
      {
        onSuccess: () => {
          setDone(true)
          setForm({ current: '', next: '', again: '' })
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
            value={form.current}
            onChange={(e) => setForm({ ...form, current: e.target.value })}
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
            value={form.next}
            onChange={(e) => setForm({ ...form, next: e.target.value })}
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
            value={form.again}
            onChange={(e) => setForm({ ...form, again: e.target.value })}
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
