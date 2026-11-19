import { useEffect, useRef, useState } from 'react'
import { formatINR } from '../lib/format'

/** Hero number count-up -- the brief's one sanctioned "purposeful" animation
 * for this screen. Respects prefers-reduced-motion by jumping straight to
 * the final value instead of animating. */
export function CountUp({ value, durationMs = 700 }: { value: number; durationMs?: number }) {
  const [display, setDisplay] = useState(0)
  const frame = useRef<number | null>(null)

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduceMotion) {
      setDisplay(value)
      return
    }
    const start = performance.now()
    function tick(now: number) {
      const progress = Math.min(1, (now - start) / durationMs)
      setDisplay(Math.round(value * (1 - Math.pow(1 - progress, 3))))
      if (progress < 1) frame.current = requestAnimationFrame(tick)
    }
    frame.current = requestAnimationFrame(tick)
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current)
    }
  }, [value, durationMs])

  return <span>{formatINR(display)}</span>
}
