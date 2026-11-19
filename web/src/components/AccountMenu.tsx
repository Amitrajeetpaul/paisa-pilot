import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useApp } from '../state/AppContext'
import { Icon } from './Icon'

export function AccountMenu() {
  const { sessionId, setSessionId, setSampleData, displayName, setDisplayName, sampleData } = useApp()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

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

  async function deleteEverything() {
    if (!sessionId) return leave()
    setBusy(true)
    try {
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
        className="border-rose text-navy flex h-9 w-9 items-center justify-center rounded-full border-2 bg-white text-sm font-bold"
      >
        {displayName ? displayName.charAt(0).toUpperCase() : <Icon name="user" size={16} />}
      </button>

      {open && (
        <div
          role="menu"
          className="border-line animate-card-entrance absolute right-0 z-50 mt-2 w-72 rounded-2xl border bg-white p-2 shadow-xl"
        >
          <div className="px-3 py-2">
            <p className="text-navy text-sm font-bold">{displayName || 'Your session'}</p>
            <p className="text-muted text-xs">{sampleData ? 'Sample profile, no real data' : 'Your documents are deleted within 24 hours'}</p>
          </div>
          <button
            role="menuitem"
            onClick={() => {
              setOpen(false)
              navigate('/app/consent')
            }}
            className="text-navy hover:bg-coral-tint flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-left text-sm font-semibold"
          >
            <Icon name="upload" size={18} /> Add or replace documents
          </button>
          {!confirming ? (
            <button
              role="menuitem"
              onClick={() => setConfirming(true)}
              className="text-navy hover:bg-coral-tint flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-left text-sm font-semibold"
            >
              <Icon name="trash" size={18} /> {sampleData ? 'Start over' : 'Delete my data'}
            </button>
          ) : (
            <div className="bg-warning-card mx-1 mb-1 rounded-xl p-3">
              <p className="text-navy text-xs leading-relaxed">
                {sampleData
                  ? 'This clears the sample profile and takes you back to the start.'
                  : 'This permanently deletes your uploads and every number you confirmed. It cannot be undone.'}
              </p>
              <div className="mt-2 flex gap-2">
                <button
                  onClick={deleteEverything}
                  disabled={busy}
                  className="bg-navy min-h-11 flex-1 rounded-xl text-sm font-semibold text-white disabled:opacity-60"
                >
                  {busy ? 'Deleting…' : 'Yes, delete'}
                </button>
                <button onClick={() => setConfirming(false)} className="text-navy min-h-11 flex-1 rounded-xl border text-sm font-semibold">
                  Keep
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
