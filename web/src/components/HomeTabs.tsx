import { useState, type ReactNode } from 'react'

export interface TabDef {
  id: string
  label: string
  content: ReactNode
}

/** One section at a time instead of a long scroll: what a busy person needs, without the noise. */
export function HomeTabs({ tabs, initial }: { tabs: TabDef[]; initial?: string }) {
  const [active, setActive] = useState(initial ?? tabs[0]?.id)
  const current = tabs.find((t) => t.id === active) ?? tabs[0]
  if (!current) return null
  return (
    <section className="mt-8">
      <div role="tablist" aria-label="Your money" className="bg-slate-500/10 flex gap-1 rounded-2xl p-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={t.id === current.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => setActive(t.id)}
            className={`min-h-11 flex-1 rounded-xl px-2 text-sm font-semibold transition-colors ${
              t.id === current.id ? 'text-ink bg-white shadow-sm' : 'text-muted hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${current.id}`} aria-labelledby={`tab-${current.id}`} className="mt-3">
        {current.content}
      </div>
    </section>
  )
}
