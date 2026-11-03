import { NavLink, Outlet } from 'react-router'
import { useTicketSummary } from '../api/queries'
import { useAuth } from '../auth/useAuth'

export function AppShell() {
  const { user, signOut } = useAuth()
  const summary = useTicketSummary()
  const pending = summary.data?.pending_proposals ?? 0

  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        İçeriğe atla
      </a>
      <nav className="rail" aria-label="Ana menü">
        <div className="wordmark" aria-label="SupportFlow">
          SupportFlow
        </div>
        <ul className="rail__links">
          <li>
            <NavLink to="/" end className="rail__link">
              Genel bakış
            </NavLink>
          </li>
          <li>
            <NavLink to="/tickets" className="rail__link">
              Talepler
              {summary.data ? (
                <span className="rail__count" title="İncelemeye hazır">
                  {summary.data.by_status.awaiting_review}
                  <span className="visually-hidden"> incelemeye hazır</span>
                </span>
              ) : null}
            </NavLink>
          </li>
          <li>
            <NavLink to="/approvals" className="rail__link">
              Onaylar
              {pending > 0 ? (
                <span className="rail__count rail__count--alert">
                  {pending}
                  <span className="visually-hidden"> bekliyor</span>
                </span>
              ) : null}
            </NavLink>
          </li>
        </ul>
        {user ? (
          <div className="rail__user">
            <span className="rail__name">{user.full_name}</span>
            <span className="meta">{user.role === 'admin' ? 'Yönetici' : 'Destek uzmanı'}</span>
            <button type="button" className="button button--quiet rail__signout" onClick={signOut}>
              Çıkış yap
            </button>
          </div>
        ) : null}
      </nav>
      <main id="main" className="workspace" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  )
}
