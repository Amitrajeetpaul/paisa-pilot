import { useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Button } from '../components/Button'
import { buildDraftText } from '../lib/drafts'
import type { MoneyFinderCard } from '../lib/api'
import { useApp } from '../state/AppContext'

export function DraftsScreen() {
  const { cardId } = useParams<{ cardId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const { t } = useApp()
  const card = (location.state as { card?: MoneyFinderCard } | null)?.card

  const initial = card ? buildDraftText(card) : { heading: cardId ?? 'Draft', body: '' }
  const [text, setText] = useState(initial.body)
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  function handleDownload() {
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${initial.heading.replace(/\s+/g, '_')}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function handleShare() {
    if (navigator.share) {
      await navigator.share({ title: initial.heading, text })
    } else {
      await handleCopy()
    }
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4 px-5 py-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          aria-label={t('common.back')}
          className="flex h-10 w-10 items-center justify-center rounded-full hover:bg-black/5"
        >
          ←
        </button>
        <h1 className="text-navy text-xl font-bold">{initial.heading}</h1>
      </div>

      <p className="text-muted text-sm">{t('drafts.editable')}</p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={12}
        className="border-line rounded-[20px] border bg-white p-4 text-sm leading-relaxed text-navy outline-none focus-visible:border-teal"
      />

      <div className="flex flex-wrap gap-3">
        <Button variant="outline" onClick={handleCopy}>
          {copied ? '✓' : t('common.copy')}
        </Button>
        <Button variant="outline" onClick={handleShare}>
          {t('common.share')}
        </Button>
        <Button variant="outline" onClick={handleDownload}>
          {t('common.download')}
        </Button>
      </div>
    </div>
  )
}
