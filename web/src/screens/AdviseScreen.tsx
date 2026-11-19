import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { Button } from '../components/Button'
import { api } from '../lib/api'
import { useApp } from '../state/AppContext'

interface Message {
  role: 'user' | 'assistant'
  text: string
  sourceChip?: string
}

const SUGGESTIONS = [
  'Which tax option is better for me?',
  'Where should my spare ₹8,000 go? My goal is 3 years away.',
  'How big should my emergency fund be?',
  'What insurance do I need?',
]

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
      <h1 className="text-navy text-xl font-bold">{t('advise.title')}</h1>

      <div className="mt-4 flex flex-1 flex-col gap-3 overflow-y-auto">
        {messages.length === 0 && (
          <div>
            <p className="text-muted text-sm">{t('advise.greeting')}</p>
            <p className="text-navy mt-4 text-xs font-bold uppercase tracking-wide">{t('advise.try')}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {SUGGESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => handleSend(q)}
                  className="border-line text-navy min-h-11 rounded-full border bg-white px-4 text-left text-sm font-medium hover:bg-black/[0.03]"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === 'user' ? 'bg-coral-tint text-navy' : 'border-line border bg-white text-navy'
              }`}
            >
              <p>{m.text}</p>
              {m.role === 'assistant' && /education, not/i.test(m.text) && (
                <p className="bg-warn-tint text-navy mt-2 rounded-lg px-2 py-1 text-xs">{t('advise.guardrailNote')}</p>
              )}
              {m.sourceChip && <p className="text-muted mt-1 text-xs">{m.sourceChip}</p>}
            </div>
          </div>
        ))}
        {sending && <p className="text-muted text-sm">{t('common.loading')}</p>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          handleSend()
        }}
        className="border-line sticky bottom-20 mt-4 flex items-center gap-2 rounded-full border bg-white p-1.5 md:bottom-4"
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
