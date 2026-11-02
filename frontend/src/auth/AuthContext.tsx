import { useQueryClient } from '@tanstack/react-query'
import { type ReactNode, useCallback, useMemo, useState } from 'react'
import { request, setAccessToken, setUnauthorizedHandler } from '../api/client'
import { useMe } from '../api/queries'
import { AuthContext, type AuthState } from './context'

// Demo auth (ADR-007): the token lives in sessionStorage so a refresh keeps you signed in,
// and closing the tab signs you out. A production app would use an identity provider.
const STORAGE_KEY = 'supportflow.token'

function readStoredToken(): string | null {
  const token = sessionStorage.getItem(STORAGE_KEY)
  setAccessToken(token)
  return token
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient()
  const [token, setToken] = useState<string | null>(readStoredToken)
  const me = useMe(token !== null)

  const signOut = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY)
    setAccessToken(null)
    setToken(null)
    client.clear()
  }, [client])

  setUnauthorizedHandler(signOut)

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await request<{ access_token: string }>('POST', '/auth/login', {
      body: { email, password },
    })
    sessionStorage.setItem(STORAGE_KEY, result.access_token)
    setAccessToken(result.access_token)
    setToken(result.access_token)
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      user: token ? me.data : undefined,
      isLoading: token !== null && me.isPending,
      signIn,
      signOut,
    }),
    [token, me.data, me.isPending, signIn, signOut],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
