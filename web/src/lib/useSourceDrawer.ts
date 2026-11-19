import { useCallback, useState } from 'react'
import { api, type SourceTrailEntry } from './api'

export function useSourceDrawer(sessionId: string | null) {
  const [entry, setEntry] = useState<SourceTrailEntry | null>(null)
  const [loading, setLoading] = useState(false)

  const open = useCallback(
    async (cardId: string) => {
      if (!sessionId) return
      setLoading(true)
      try {
        const result = await api.getSourceTrail(sessionId, cardId)
        setEntry(result)
      } catch {
        setEntry({
          card_id: cardId,
          label: cardId,
          inputs_used: {},
          rule_or_formula: 'Source details are not available for this card yet.',
          config_version: null,
          source_url: null,
        })
      } finally {
        setLoading(false)
      }
    },
    [sessionId],
  )

  const close = useCallback(() => setEntry(null), [])

  return { entry, loading, open, close }
}
