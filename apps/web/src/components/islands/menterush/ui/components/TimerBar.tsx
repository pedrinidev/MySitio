import styles from './components.module.css'

/** Barra de tiempo restante. Late en rojo en el tramo final. */
export function TimerBar({
  remainingMs,
  totalMs,
  urgentBelowMs = 1500,
}: {
  remainingMs: number
  totalMs: number
  urgentBelowMs?: number
}) {
  const ratio = totalMs > 0 ? Math.min(Math.max(remainingMs / totalMs, 0), 1) : 0
  const urgent = remainingMs <= urgentBelowMs

  return (
    <div
      className={styles.timerTrack}
      role="progressbar"
      aria-label="Tiempo restante"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(ratio * 100)}
    >
      <div
        className={`${styles.timerFill} ${urgent ? styles.urgent : ''}`}
        style={{ transform: `scaleX(${ratio})` }}
      />
    </div>
  )
}
