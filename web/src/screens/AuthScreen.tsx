import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../components/Button'
import { Wordmark } from '../components/Logo'
import { ThemeToggle } from '../components/ThemeToggle'
import { api, rememberSavingOn } from '../lib/api'
import { pushCurrentDocs, restoreFromAccount } from '../lib/account'
import { AuthError, sendPasswordReset, signIn, signUp } from '../lib/auth'
import { isSampleSession } from '../lib/clientSession'
import { useApp } from '../state/AppContext'

type Mode = 'in' | 'up' | 'reset'

export function AuthScreen() {
  const navigate = useNavigate()
  const { sessionId, setSessionId, setSampleData, setDisplayName } = useApp()
  const [mode, setMode] = useState<Mode>('in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [save, setSave] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setInfo(null)
    setBusy(true)
    try {
      if (mode === 'reset') {
        await sendPasswordReset(email)
        setInfo('If that email has an account, we have sent a link to choose a new password.')
        return
      }
      if (mode === 'up') await signUp(email, password)
      else await signIn(email, password)

      const me = await api.me()
      // The built-in sample profile belongs to nobody: never carry it into a real account.
      const ownSession = sessionId && !isSampleSession(sessionId) ? sessionId : null
      const startClean = () => {
        setSessionId(null)
        setSampleData(false)
        setDisplayName('')
      }
      if (mode === 'up' && save) {
        await api.meConsent(true)
        rememberSavingOn(true)
        if (ownSession) await pushCurrentDocs(ownSession)
        else startClean()
        navigate(ownSession ? '/app/home' : '/app/consent')
        return
      }
      rememberSavingOn(me.saving_on)
      const restored = await restoreFromAccount(me, { setSessionId, setSampleData, setDisplayName })
      if (restored > 0) {
        navigate('/app/home')
      } else if (ownSession) {
        navigate('/app/home')
      } else {
        startClean()
        navigate('/app/consent')
      }
    } catch (err) {
      setError(
        err instanceof AuthError
          ? err.message
          : 'Signed in, but we could not reach our server to load your saved details. Please try again in a moment.',
      )
    } finally {
      setBusy(false)
    }
  }

  const title = mode === 'in' ? 'Welcome back' : mode === 'up' ? 'Create your account' : 'Reset your password'

  return (
    <div className="text-ink mx-auto flex min-h-screen max-w-md flex-col px-5" style={{ paddingTop: 'max(env(safe-area-inset-top), 1.5rem)' }}>
      <header className="flex items-center justify-between py-4">
        <Link to="/" aria-label="Paisa Pilot home">
          <Wordmark />
        </Link>
        <ThemeToggle />
      </header>

      <main className="flex-1 py-6">
        <h1 className="text-2xl font-extrabold tracking-tight">{title}</h1>
        <p className="text-muted mt-1 text-sm">
          {mode === 'up'
            ? 'An account lets Paisa Pilot remember your documents and how your money changes from visit to visit.'
            : mode === 'in'
              ? 'Sign in to pick up where you left off.'
              : 'Enter your email and we will send you a link.'}
        </p>

        <form onSubmit={submit} className="card mt-5 space-y-3 p-4">
          <label className="block text-sm font-semibold">
            Email
            <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className="border-line bg-white mt-1 min-h-11 w-full rounded-xl border px-3 text-base font-normal" />
          </label>
          {mode !== 'reset' && (
            <label className="block text-sm font-semibold">
              Password
              <input
                type="password"
                required
                minLength={8}
                autoComplete={mode === 'up' ? 'new-password' : 'current-password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="border-line bg-white mt-1 min-h-11 w-full rounded-xl border px-3 text-base font-normal"
              />
              {mode === 'up' && <span className="text-muted mt-1 block text-xs font-normal">At least 8 characters.</span>}
            </label>
          )}

          {mode === 'up' && (
            <label className="bg-slate-500/10 flex items-start gap-3 rounded-xl p-3 text-sm">
              <input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} className="mt-1 h-5 w-5 shrink-0" />
              <span>
                <b>Remember my details.</b> Keep the values I confirm from my documents, the results we work out, and a short note of my questions in my account, so my advice improves over time. I can turn this off or delete everything at any time.{' '}
                <Link to="/privacy" className="underline">Privacy notice</Link>
              </span>
            </label>
          )}

          {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
          {info && <p className="text-sm text-emerald-600" role="status">{info}</p>}

          <Button type="submit" variant="primary" loading={busy} className="w-full">
            {mode === 'in' ? 'Sign in' : mode === 'up' ? 'Create account' : 'Send reset link'}
          </Button>
        </form>

        <div className="mt-4 flex flex-col items-center gap-2 text-sm">
          {mode === 'in' && (
            <>
              <button type="button" className="text-coral-dark min-h-11 font-semibold underline" onClick={() => { setMode('up'); setError(null) }}>
                New here? Create an account
              </button>
              <button type="button" className="text-muted min-h-11 underline" onClick={() => { setMode('reset'); setError(null) }}>
                Forgot your password?
              </button>
            </>
          )}
          {mode !== 'in' && (
            <button type="button" className="text-coral-dark min-h-11 font-semibold underline" onClick={() => { setMode('in'); setError(null); setInfo(null) }}>
              Back to sign in
            </button>
          )}
          <Link to="/app/consent" className="text-muted min-h-11 pt-2 underline">
            Continue without an account
          </Link>
        </div>
        <p className="text-muted mt-6 text-center text-xs">
          Your password goes straight to Google's sign-in service. We never see it.
        </p>
      </main>
    </div>
  )
}
