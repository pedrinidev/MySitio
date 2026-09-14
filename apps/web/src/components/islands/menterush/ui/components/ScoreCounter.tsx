import { useEffect, useRef, useState } from 'react'
import styles from './components.module.css'

/**
 * Puntuación que cuenta hacia arriba en lugar de saltar: ver subir el número es
 * parte de la recompensa.
 */
export function ScoreCounter({ value, durationMs = 420 }: { value: number; durationMs?: number }) {
  const [shown, setShown] = useState(value)
  const fromRef = useRef(value)
  const frameRef = useRef(0)

  useEffect(() => {
    const from = fromRef.current
    if (from === value) return

    const start = performance.now()
    const step = (now: number) => {
      const t = Math.min((now - start) / durationMs, 1)
      // Ease-out: arranca rápido y frena al llegar.
      const eased = 1 - Math.pow(1 - t, 3)
      setShown(Math.round(from + (value - from) * eased))
      if (t < 1) frameRef.current = requestAnimationFrame(step)
      else fromRef.current = value
    }

    frameRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frameRef.current)
  }, [value, durationMs])

  return <span className={`${styles.score} tabular`}>{shown}</span>
}
