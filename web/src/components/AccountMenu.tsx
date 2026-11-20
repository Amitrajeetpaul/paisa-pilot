import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { pushCurrentDocs } from '../lib/account'
import { api, rememberSavingOn, savingOn } from '../lib/api'
import { deleteAuthAccount, signOut, useAuth } from '../lib/auth'
import { track } from '../lib/track'
import { useApp } from '../state/AppContext'
import { Icon } from './Icon'

export function AccountMenu() {
  const { t, sessionId, setSessionId, setSampleData, displayName, setDisplayName, sampleData } = useApp()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const user = useAuth()
  const [saving, setSaving] = useState<boolean>(() => savingOn())
  const [note, setNote] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
        setConfirming(false)
      }
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        setConfirming(false)
      }
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  function leave() {
    setSessionId(null)
    setSampleData(false)
    setDisplayName('')
    setOpen(false)
    setConfirming(false)
    // Full navigation: avoids the app redirecting a session-less page to the upload screen first.
    window.location.assign('/')
  }

  async function toggleSaving() {
    setBusy(true)
    setNote(null)
    try {
      const next = !saving
      await api.meConsent(next)
      rememberSavingOn(next)
      setSaving(next)
      if (next && sessionId) {
        const n = await pushCurrentDocs(sessionId)
        setNote(n > 0 ? `Saved ${n} document${n === 1 ? '' : 's'} to your account.` : 'Saving is on. New documents you confirm will be kept.')
      } else if (!next) {
        setNote('Saving is off. Nothing new will be kept. Your earlier data stays until you delete it.')
      }
    } catch {
      setNote('Could not change that right now. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  function doSignOut() {
    signOut()
    leave()
  }

  async function deleteEverything() {
    setBusy(true)
    if (user) {
      try {
        await api.meDelete() // our copy first, then the sign-in account itself
        await deleteAuthAccount()
        rememberSavingOn(false)
      } catch {
        /* if the server is unreachable the person can try again; do not pretend it worked */
        setNote('We could not delete your account just now. Please try again in a moment.')
        setBusy(false)
        return
      }
    }
    if (!sessionId) return leave()
    try {
      track('data_deleted')
      await api.deleteMyData(sessionId)
    } catch {
      /* session may already be gone (expired); clearing locally is still right */
    } finally {
      setBusy(false)
      leave()
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        className="border-rose text-ink flex h-9 w-9 items-center justify-center rounded-full border-2 bg-white text-sm font-bold"
      >
        {displayName ? displayName.charAt(0).toUpperCase() : <Icon name="user" size={16} />}
      </button>

      {open && (
        <div
          role="menu"
          className="border-line animate-card-entrance absolute right-0 z-50 mt-2 w-72 rounded-2xl border bg-white p-2 shadow-xl"
        >
          <div className="px-3 py-2">
            <p className="text-ink text-sm font-bold">{displayName || t('account.session')}</p>
            <p className="text-muted break-all text-xs">{user ? user.email : sampleData ? t('account.sampleNote') : t('account.realNote')}</p>
          </div>
          {!user ? (
            <button
              role="menuitem"
              onClick={() => {
                setOpen(false)
                navigate('/login')
              }}
              className="text-ink hover:bg-coral-tint flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-left text-sm font-semibold"
            >
              <Icon name="user" size={18} /> Sign in or create account
            </button>
          ) : (
            <>
              <button
                role="menuitemcheckbox"
                aria-checked={saving}
                onClick={toggleSaving}
                disabled={busy}
                className="text-ink hover:bg-coral-tint flex min-h-11 w-full items-center justify-between gap-3 rounded-xl px-3 text-left text-sm font-semibold disabled:opacity-60"
              >
                <span className="flex items-center gap-3"><Icon name="lock" size={18} /> Remember my details</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${saving ? 'bg-emerald-500/15 text-emerald-600' : 'bg-slate-500/15 text-muted'}`}>{saving ? 'On' : 'Off'}</span>
              </button>
              {note && <p className="text-muted px-3 pb-1 text-xs" role="status">{note}</p>}
            </>
          )}
          <button
            role="menuitem"
            onClick={() => {
              setOpen(false)
              navigate('/app/consent')
            }}
            className="text-ink hover:bg-coral-tint flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-left text-sm font-semibold"
          >
            <Icon name="upload" size={18} /> {t('account.add')}
          </button>
          {user && (
            <button
              role="menuitem"
              onClick={doSignOut}
              className="text-ink hover:bg-coral-tint flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-left text-sm font-semibold"
            >
              <Icon name="user" size={18} /> Sign out
            </button>
          )}
          {!confirming ? (
            <button
              role="menuitem"
              onClick={() => setConfirming(true)}
              className="text-ink hover:bg-coral-tint flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-left text-sm font-semibold"
            >
              <Icon name="trash" size={18} /> {user ? 'Delete my account and data' : sampleData ? t('account.startOver') : t('account.delete')}
            </button>
          ) : (
            <div className="bg-warning-card mx-1 mb-1 rounded-xl p-3">
              <p className="text-ink text-xs leading-relaxed">
                {user ? 'This permanently deletes your account, your saved documents and your history. It cannot be undone.' : sampleData ? t('account.confirmSample') : t('account.confirmReal')}
              </p>
              <div className="mt-2 flex gap-2">
                <button
                  onClick={deleteEverything}
                  disabled={busy}
                  className="bg-navy min-h-11 flex-1 rounded-xl text-sm font-semibold text-white disabled:opacity-60"
                >
                  {busy ? t('account.deleting') : t('account.yes')}
                </button>
                <button onClick={() => setConfirming(false)} className="text-ink min-h-11 flex-1 rounded-xl border text-sm font-semibold">
                  {t('account.keep')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
