import { type FormEvent, useState } from 'react'
import { ApiError } from '../api/client'
import { useCreateUser, useUpdateUser, useUsers } from '../api/queries'
import type { User, UserRole } from '../api/types'
import { useAuth } from '../auth/useAuth'

const ROLE_LABEL: Record<UserRole, string> = { agent_user: 'Destek uzmanı', admin: 'Yönetici' }
const MIN_PASSWORD = 12

/** Admin: the installation's staff accounts (ADR-017). */
export function TeamPage() {
  const { user: me } = useAuth()
  const users = useUsers(true)

  return (
    <div className="page">
      <header className="page__head">
        <h1>Ekip</h1>
        <p className="muted page__lede">
          SupportFlow'u kullanan çalışanlar. Destek uzmanları talepleri görür ve adres değişikliklerini
          onaylar; iadeleri ve ekibi yalnızca yöneticiler yönetir.
        </p>
      </header>

      <AddMemberForm />

      {users.isPending ? <p className="loading">Ekip yükleniyor…</p> : null}
      {users.isError ? (
        <p className="notice notice--error" role="alert">
          Ekip yüklenemedi. {users.error.message}
        </p>
      ) : null}
      {users.data ? (
        <table className="ticket-table">
          <caption className="visually-hidden">Ekip üyeleri</caption>
          <thead>
            <tr>
              <th scope="col">Ad</th>
              <th scope="col">Rol</th>
              <th scope="col">Durum</th>
              <th scope="col">
                <span className="visually-hidden">İşlemler</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {users.data.map((member) => (
              <MemberRow key={member.id} member={member} isMe={member.id === me?.id} />
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  )
}

function MemberRow({ member, isMe }: { member: User; isMe: boolean }) {
  const update = useUpdateUser()
  const [error, setError] = useState<string | null>(null)

  function change(body: { role?: UserRole; is_active?: boolean; password?: string }) {
    setError(null)
    update.mutate(
      { id: member.id, ...body },
      { onError: (err) => setError(err instanceof ApiError ? err.message : 'Değişiklik kaydedilemedi.') },
    )
  }

  function resetPassword() {
    const password = window.prompt(
      `${member.full_name} için yeni parola (en az ${MIN_PASSWORD} karakter). Kişiye güvenli bir yoldan iletin.`,
    )
    if (password) change({ password })
  }

  const otherRole: UserRole = member.role === 'admin' ? 'agent_user' : 'admin'
  return (
    <tr>
      <td>
        <span className="ticket-table__who">
          <strong>{member.full_name}</strong>
          {isMe ? <span className="meta"> (siz)</span> : null}
        </span>
        <span className="meta">{member.email}</span>
        {error ? (
          <p className="notice notice--error" role="alert">
            {error}
          </p>
        ) : null}
      </td>
      <td>{ROLE_LABEL[member.role]}</td>
      <td>{member.is_active ? 'Etkin' : 'Pasif'}</td>
      <td>
        <div className="team__actions">
          {isMe ? null : (
            <>
              <button
                type="button"
                className="button button--quiet"
                disabled={update.isPending}
                onClick={() => change({ role: otherRole })}
              >
                {otherRole === 'admin' ? 'Yönetici yap' : 'Destek uzmanı yap'}
              </button>
              <button
                type="button"
                className="button button--quiet"
                disabled={update.isPending}
                onClick={() => change({ is_active: !member.is_active })}
              >
                {member.is_active ? 'Pasifleştir' : 'Etkinleştir'}
              </button>
              <button
                type="button"
                className="button button--quiet"
                disabled={update.isPending}
                onClick={resetPassword}
              >
                Parolayı sıfırla
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

function AddMemberForm() {
  const create = useCreateUser()
  const empty = { full_name: '', email: '', password: '', role: 'agent_user' as UserRole }
  const [form, setForm] = useState(empty)
  const [error, setError] = useState<string | null>(null)
  const [added, setAdded] = useState<string | null>(null)

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setAdded(null)
    create.mutate(form, {
      onSuccess: (user) => {
        setAdded(`${user.full_name} eklendi. Geçici parolayı kişiye güvenli bir yoldan iletin.`)
        setForm(empty)
      },
      onError: (err) => setError(err instanceof ApiError ? err.message : 'Hesap eklenemedi.'),
    })
  }

  return (
    <form className="sheet team__form" onSubmit={onSubmit} aria-labelledby="add-member">
      <h2 id="add-member" className="sheet__title">
        Ekip üyesi ekle
      </h2>
      <div className="team__fields">
        <div className="field">
          <label htmlFor="member-name">Ad soyad</label>
          <input
            id="member-name"
            className="input"
            required
            maxLength={120}
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="member-email">E-posta</label>
          <input
            id="member-email"
            className="input"
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="member-password">Geçici parola</label>
          <input
            id="member-password"
            className="input"
            type="text"
            required
            minLength={MIN_PASSWORD}
            autoComplete="off"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="member-role">Rol</label>
          <select
            id="member-role"
            className="select"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
          >
            <option value="agent_user">{ROLE_LABEL.agent_user}</option>
            <option value="admin">{ROLE_LABEL.admin}</option>
          </select>
        </div>
      </div>
      {error ? (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      ) : null}
      {added ? (
        <p className="notice notice--success" role="status">
          {added}
        </p>
      ) : null}
      <div>
        <button className="button button--primary" type="submit" disabled={create.isPending}>
          {create.isPending ? 'Ekleniyor…' : 'Ekle'}
        </button>
      </div>
    </form>
  )
}
