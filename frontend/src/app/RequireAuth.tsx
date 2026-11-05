import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { useAuth } from '../auth/useAuth'
import { LandingPage } from '../pages/LandingPage'
import { showLanding } from './landing'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()
  const location = useLocation()
  if (isLoading) return <p className="loading">Çalışma alanınız yükleniyor…</p>
  if (!user) {
    // Signed-out visitors to the demo's home page get the product page instead of a login wall.
    if (location.pathname === '/' && showLanding()) return <LandingPage />
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}

/** Admin-only screens. The API enforces the role anyway; this only avoids a dead end. */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (user?.role !== 'admin') return <Navigate to="/" replace />
  return children
}
