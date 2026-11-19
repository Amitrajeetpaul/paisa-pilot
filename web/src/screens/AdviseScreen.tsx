import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { Button } from '../components/Button'
import { Icon } from '../components/Icon'
import { api } from '../lib/api'
import { track } from '../lib/track'
import { useApp } from '../state/AppContext'

interface Message {
  role: 'user' | 'assistant'
  text: string
  sourceChip?: string
}

const SUGGESTIONS = [
  { key: 'advise.s1', question: 'Which tax option is better for me?' },
  { key: 'advise.s2', question: 'Where should my spare ₹8,000 go? My goal is 3 years away.' },
  { key: 'advise.s3', question: 'How big should my emergency fund be?' },
  { key: 'advise.s4', question: 'What insurance do I need?' },
] as const

export function AdviseScreen() {
  const { t, sessionId } = useApp()
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  useEffect(() => {
    if (!sessionId) navigate('/app/consent')
  }, [sessionId, navigate])

  async function handleSend(preset?: string) {
    const question = (preset ?? input).trim()
    if (!question || !sessionId) return
    track('advise_question')
    setMessages((prev) => [...prev, { role: 'user', text: question }])
    setInput('')
    setSending(true)
    try {
      const result = await api.askConsultant(sessionId, question)
      setMessages((prev) => [...prev, { role: 'assistant', text: result.answer, sourceChip: result.source_chip }])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: 'Sorry, I could not answer that right now. Please try again.' },
      ])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col py-6" style={{ minHeight: 'calc(100vh - 7rem)' }}>
      <h1 className="text-navy text-2xl font-extrabold tracking-tight">{t('advise.title')}</h1>

      <div className="mt-4 flex flex-1 flex-col gap-3 overflow-y-auto">
        {messages.length === 0 && (
          <div>
            <p className="text-muted text-sm">{t('advise.greeting')}</p>
            <p className="text-navy mt-4 text-xs font-bold uppercase tracking-wide">{t('advise.try')}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {SUGGESTIONS.map((q) => (
                <button
                  key={q.key}
                  type="button"
                  onClick={() => handleSend(q.question)}
                  className="border-line text-navy min-h-11 rounded-full border bg-white px-4 text-left text-sm font-medium hover:bg-black/[0.03]"
                >
                  {t(q.key)}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`stagger flex items-end gap-2 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {m.role === 'assistant' && (
              <span className="bg-coral-button text-navy flex h-8 w-8 shrink-0 items-center justify-center rounded-full shadow-sm" aria-hidden="true">
                <Icon name="chat" size={16} />
              </span>
            )}
            <div
              className={`max-w-[82%] px-4 py-3 text-sm leading-relaxed shadow-sm ${
                m.role === 'user'
                  ? 'bg-navy rounded-[20px] rounded-br-md text-white'
                  : 'card text-navy rounded-[20px] rounded-bl-md'
              }`}
            >
              <p className="whitespace-pre-line">{m.text}</p>
              {m.role === 'assistant' && /education, not/i.test(m.text) && (
                <p className="bg-warn-tint text-navy mt-2 rounded-lg px-2 py-1 text-xs">{t('advise.guardrailNote')}</p>
              )}
              {m.sourceChip && <p className="text-muted mt-1.5 text-[11px] font-medium">{m.sourceChip}</p>}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex items-end gap-2" role="status" aria-label="Thinking">
            <span className="bg-coral-button text-navy flex h-8 w-8 shrink-0 items-center justify-center rounded-full shadow-sm" aria-hidden="true">
              <Icon name="chat" size={16} />
            </span>
            <div className="card flex items-center gap-1.5 rounded-[20px] rounded-bl-md px-4 py-3.5">
              <span className="typing-dot" />
              <span className="typing-dot" style={{ animationDelay: '0.15s' }} />
              <span className="typing-dot" style={{ animationDelay: '0.3s' }} />
            </div>
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          handleSend()
        }}
        className="glass border-line sticky bottom-24 mt-4 flex items-center gap-2 rounded-full border p-1.5 shadow-[0_8px_24px_-12px_rgba(34,34,59,0.3)] md:bottom-4"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t('advise.placeholder')}
          className="min-h-11 flex-1 bg-transparent px-3 text-sm outline-none"
          aria-label={t('advise.placeholder')}
        />
        <Button type="submit" variant="primary" disabled={!input.trim()} loading={sending}>
          {t('advise.send')}
        </Button>
      </form>
    </div>
  )
}
