import { useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { ApiError, request } from '../api/client'
import { keys, useSetupStatus } from '../api/queries'
import type { SetupRequest } from '../api/types'
import { useAuth } from '../auth/useAuth'

const MIN_PASSWORD = 12

/** First-run setup of a self-hosted installation (ADR-017): the business and its first admin. */
export function SetupPage() {
  const status = useSetupStatus()
  const { acceptToken } = useAuth()
  const client = useQueryClient()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    organization_name: '',
    full_name: '',
    email: '',
    password: '',
    password_again: '',
    setup_token: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (status.data && !status.data.setup_required) return <Navigate to="/login" replace />

  const tokenRequired = status.data?.setup_token_required ?? false
  const set = (field: keyof typeof form) => (event: { target: { value: string } }) =>
    setForm((current) => ({ ...current, [field]: event.target.value }))

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (form.password !== form.password_again) {
      setError('Parolalar birbirini tutmuyor.')
      return
    }
    setBusy(true)
    setError(null)
    const body: SetupRequest = {
      organization_name: form.organization_name,
      full_name: form.full_name,
      email: form.email,
      password: form.password,
      setup_token: tokenRequired ? form.setup_token : null,
    }
    try {
      const result = await request<{ access_token: string }>('POST', '/setup', { body })
      acceptToken(result.access_token)
      await client.invalidateQueries({ queryKey: keys.setup })
      navigate('/', { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        await client.invalidateQueries({ queryKey: keys.setup })
      }
      setError(err instanceof ApiError ? err.message : 'Kurulum tamamlanamadı. Tekrar deneyin.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <div className="login__panel">
        <div className="wordmark wordmark--large">SupportFlow</div>
        <div>
          <h1 className="setup__title">Kuruluma hoş geldiniz</h1>
          <p className="login__intro">
            İşletmenizi tanımlayın ve ilk yönetici hesabını oluşturun. Ekip arkadaşlarınızı sonra
            “Ekip” sayfasından eklersiniz.
          </p>
        </div>
        {status.isError ? (
          <p className="notice notice--error" role="alert">
            Kurulum durumu alınamadı. {status.error.message}
          </p>
        ) : null}
        <form className="login__form" onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="organization">İşletme adı</label>
            <input
              id="organization"
              className="input"
              required
              maxLength={120}
              autoComplete="organization"
              value={form.organization_name}
              onChange={set('organization_name')}
            />
          </div>
          <div className="field">
            <label htmlFor="full-name">Adınız ve soyadınız</label>
            <input
              id="full-name"
              className="input"
              required
              maxLength={120}
              autoComplete="name"
              value={form.full_name}
              onChange={set('full_name')}
            />
          </div>
          <div className="field">
            <label htmlFor="email">İş e-postası</label>
            <input
              id="email"
              className="input"
              type="email"
              required
              autoComplete="username"
              value={form.email}
              onChange={set('email')}
            />
          </div>
          <div className="field">
            <label htmlFor="password">Parola</label>
            <input
              id="password"
              className="input"
              type="password"
              required
              minLength={MIN_PASSWORD}
              autoComplete="new-password"
              aria-describedby="password-hint"
              value={form.password}
              onChange={set('password')}
            />
            <span id="password-hint" className="meta">
              En az {MIN_PASSWORD} karakter. Birkaç kelimelik bir cümle iyi bir paroladır.
            </span>
          </div>
          <div className="field">
            <label htmlFor="password-again">Parola (tekrar)</label>
            <input
              id="password-again"
              className="input"
              type="password"
              required
              autoComplete="new-password"
              value={form.password_again}
              onChange={set('password_again')}
            />
          </div>
          {tokenRequired ? (
            <div className="field">
              <label htmlFor="setup-token">Kurulum kodu</label>
              <input
                id="setup-token"
                className="input"
                required
                autoComplete="off"
                spellCheck={false}
                aria-describedby="setup-token-hint"
                value={form.setup_token}
                onChange={set('setup_token')}
              />
              <span id="setup-token-hint" className="meta">
                Kurulum betiğinin ekrana yazdığı kod; <code>.env</code> dosyasında{' '}
                <code>SETUP_TOKEN</code> olarak da durur.
              </span>
            </div>
          ) : null}
          {error ? (
            <p className="notice notice--error" role="alert">
              {error}
            </p>
          ) : null}
          <button className="button button--primary" type="submit" disabled={busy || status.isPending}>
            {busy ? 'Kuruluyor…' : 'Kurulumu tamamla'}
          </button>
        </form>
      </div>
      <aside className="intro" aria-labelledby="setup-next">
        <h2 id="setup-next" className="intro__title">
          Kurulumdan sonra
        </h2>
        <ol className="intro__steps">
          <li className="intro__step">
            <span className="intro__num">1</span>
            <div>
              <strong>Ekibinizi ekleyin</strong>
              <p className="muted">Destek uzmanları talepleri görür ve adres değişikliklerini onaylar.</p>
            </div>
          </li>
          <li className="intro__step">
            <span className="intro__num">2</span>
            <div>
              <strong>Talepleri bağlayın</strong>
              <p className="muted">E-posta kutusu bağlantısı sıradaki sürümde geliyor.</p>
            </div>
          </li>
          <li className="intro__step">
            <span className="intro__num">3</span>
            <div>
              <strong>Kararı yine insan verir</strong>
              <p className="muted">Yapay zekâ taslak ve öneri hazırlar; hiçbir değişikliği kendisi yapmaz.</p>
            </div>
          </li>
        </ol>
      </aside>
    </div>
  )
}
