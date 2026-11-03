import { createContext } from 'react'
import type { User } from '../api/types'

export interface AuthState {
  user: User | undefined
  isLoading: boolean
  signIn: (email: string, password: string) => Promise<void>
  /** Start a session with a token the API already issued (first-run setup). */
  acceptToken: (token: string) => void
  signOut: () => void
}

export const AuthContext = createContext<AuthState | null>(null)
