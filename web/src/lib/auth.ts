import { useSyncExternalStore } from 'react'

/**
 * Sign-in with Google Identity Platform (email + password), called straight from the browser.
 * We never see or store the password: it goes to Google, and we keep only the short-lived ID token
 * (sent to our API as a Bearer token) and a refresh token on this device.
 *
 * The key below is a public web key restricted to the sign-in services; it is meant to ship in the app.
 */
const AUTH_KEY = import.meta.env.VITE_AUTH_API_KEY ?? 'AIzaSyCwVNhMJpeGEw8E3IcYrcWGKRBWPdZ18j4'
const IDT = 'https://identitytoolkit.googleapis.com/v1'
const STORE = 'pp_auth_v1'

export interface AuthUser {
  uid: string
  email: string
  idToken: string
  refreshToken: string
  expiresAt: number // ms since epoch
}

let current: AuthUser | null = readStored()
const listeners = new Set<() => void>()

function readStored(): AuthUser | null {
  try {
    const raw = localStorage.getItem(STORE)
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
}

function setUser(u: AuthUser | null) {
  current = u
  try {
    if (u) localStorage.setItem(STORE, JSON.stringify(u))
    else localStorage.removeItem(STORE)
  } catch {
    /* private mode: the person just signs in again next time */
  }
  listeners.forEach((l) => l())
}

const subscribe = (cb: () => void) => {
  listeners.add(cb)
  return () => listeners.delete(cb)
}

/** The signed-in person, or null. Re-renders when they sign in or out. */
export function useAuth(): AuthUser | null {
  return useSyncExternalStore(subscribe, () => current)
}

export const currentUser = () => current

export class AuthError extends Error {}

const MESSAGES: Record<string, string> = {
  EMAIL_EXISTS: 'That email already has an account. Try signing in.',
  EMAIL_NOT_FOUND: 'We could not find an account with that email.',
  INVALID_PASSWORD: 'That password is not right.',
  INVALID_LOGIN_CREDENTIALS: 'The email or password is not right.',
  INVALID_EMAIL: 'Please enter a valid email address.',
  MISSING_PASSWORD: 'Please enter a password.',
  WEAK_PASSWORD: 'Please choose a password with at least 8 characters.',
  USER_DISABLED: 'This account has been switched off. Please contact us.',
  TOO_MANY_ATTEMPTS_TRY_LATER: 'Too many tries. Please wait a few minutes and try again.',
  OPERATION_NOT_ALLOWED: 'Sign-in is not available right now. Please try again later.',
}

async function call<T>(path: string, body: Record<string, unknown>): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${IDT}/${path}?key=${AUTH_KEY}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  } catch {
    throw new AuthError('Could not reach the sign-in service. Please check your internet and try again.')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const code = String(data?.error?.message ?? '').split(' ')[0]
    throw new AuthError(MESSAGES[code] ?? 'Something went wrong. Please try again.')
  }
  return data as T
}

interface SignInResponse {
  localId: string
  email: string
  idToken: string
  refreshToken: string
  expiresIn: string
}

function adopt(r: SignInResponse) {
  setUser({ uid: r.localId, email: r.email, idToken: r.idToken, refreshToken: r.refreshToken, expiresAt: Date.now() + Number(r.expiresIn) * 1000 })
}

export async function signUp(email: string, password: string) {
  adopt(await call<SignInResponse>('accounts:signUp', { email: email.trim(), password, returnSecureToken: true }))
}

export async function signIn(email: string, password: string) {
  adopt(await call<SignInResponse>('accounts:signInWithPassword', { email: email.trim(), password, returnSecureToken: true }))
}

export async function sendPasswordReset(email: string) {
  await call('accounts:sendOobCode', { requestType: 'PASSWORD_RESET', email: email.trim() })
}

export function signOut() {
  setUser(null)
}

/** A valid ID token for API calls (refreshed when it is about to expire), or null if signed out. */
export async function getIdToken(): Promise<string | null> {
  const u = current
  if (!u) return null
  if (u.expiresAt - Date.now() > 60_000) return u.idToken
  try {
    const res = await fetch(`https://securetoken.googleapis.com/v1/token?key=${AUTH_KEY}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `grant_type=refresh_token&refresh_token=${encodeURIComponent(u.refreshToken)}`,
    })
    if (!res.ok) {
      setUser(null) // the refresh token was revoked or the account is gone
      return null
    }
    const d = await res.json()
    setUser({ ...u, idToken: d.id_token, refreshToken: d.refresh_token ?? u.refreshToken, expiresAt: Date.now() + Number(d.expires_in) * 1000 })
    return d.id_token as string
  } catch {
    return u.idToken // offline: let the request try; the server will say if it is expired
  }
}

/** Permanently delete the sign-in account itself (our stored data is deleted separately, first). */
export async function deleteAuthAccount() {
  const token = await getIdToken()
  if (!token) return
  await call('accounts:delete', { idToken: token })
  setUser(null)
}
