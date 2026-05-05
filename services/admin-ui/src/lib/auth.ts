import { useSyncExternalStore } from 'react'

export type AuthUser = {
  id: number
  username: string
  full_name: string
  role: string
  branch_id: string | null
}

type AuthState = {
  token: string | null
  user: AuthUser | null
}

const TOKEN_KEY = 'vidhisa.auth.token'
const USER_KEY = 'vidhisa.auth.user'

function read(): AuthState {
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    const userRaw = localStorage.getItem(USER_KEY)
    return { token, user: userRaw ? JSON.parse(userRaw) : null }
  } catch {
    return { token: null, user: null }
  }
}

let state: AuthState = read()
const listeners = new Set<() => void>()

function emit() {
  listeners.forEach((fn) => fn())
}

export function getAuth(): AuthState {
  return state
}

export function getToken(): string | null {
  return state.token
}

export function setSession(token: string, user: AuthUser): void {
  state = { token, user }
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
  emit()
}

export function clearSession(): void {
  state = { token: null, user: null }
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  emit()
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function useAuth(): AuthState {
  return useSyncExternalStore(subscribe, getAuth, getAuth)
}
