import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { useAuth } from '../auth/useAuth'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()
  const location = useLocation()
  if (isLoading) return <p className="loading">Loading your workspace…</p>
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return children
}

/** Admin-only screens. The API enforces the role anyway; this only avoids a dead end. */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (user?.role !== 'admin') return <Navigate to="/" replace />
  return children
}
