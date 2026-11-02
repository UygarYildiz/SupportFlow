import { createContext } from 'react'
import type { User } from '../api/types'

export interface AuthState {
  user: User | undefined
  isLoading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => void
}

export const AuthContext = createContext<AuthState | null>(null)
