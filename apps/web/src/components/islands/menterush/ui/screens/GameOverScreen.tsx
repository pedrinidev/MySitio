import { useEffect } from 'react'
import type { GameEngine } from '../../application'
import styles from './screens.module.css'

/**
 * Resultado final. El reinicio es el camino crítico: `Espacio` o `Enter` vuelven
 * a jugar sin pasar por el menú.
 */
export function GameOverScreen({ engine }: { engine: GameEngine }) {
  const { state, stats, restart, home } = engine
  const practicando = state.play === 'PRACTICA'

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault()
        restart()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [restart])

  const accuracy =
    state.totalAnswers > 0 ? Math.round((state.correctAnswers / state.totalAnswers) * 100) : 0

  return (
    <div className={styles.screen}>

      <div>
        <span className={styles.finalLabel}>{practicando ? 'Aciertos' : 'Puntuación'}</span>
        <div className={`${styles.finalScore} tabular`}>
          {practicando ? `${state.correctAnswers}/${state.totalAnswers}` : state.score}
        </div>
        {practicando ? (
          <span className={styles.finalLabel}>
            {state.correctAnswers === state.totalAnswers
              ? '¡Sesión perfecta!'
              : '¡Buen trabajo! Prueba otra vez.'}
          </span>
        ) : state.isNewRecord ? (
          <span className={styles.recordBanner}>¡Nuevo récord!</span>
        ) : (
          <span className={styles.finalLabel}>Récord: {stats.record}</span>
        )}
      </div>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          {/* En práctica, "rondas superadas" repetiría el 8/10 del titular. */}
          <span className={`${styles.statValue} tabular`}>
            {practicando ? state.totalAnswers - state.correctAnswers : state.roundsCleared}
          </span>
          <span className={styles.statLabel}>{practicando ? 'Fallos' : 'Rondas'}</span>
        </div>
        <div className={styles.statCard}>
          <span className={`${styles.statValue} tabular`}>{state.bestCombo}</span>
          <span className={styles.statLabel}>Mejor racha</span>
        </div>
        <div className={styles.statCard}>
          <span className={`${styles.statValue} tabular`}>{accuracy}%</span>
          <span className={styles.statLabel}>Precisión</span>
        </div>
        <div className={styles.statCard}>
          {/* En práctica, "rondas jugadas" siempre sería 10: los puntos, que
              recogen las rachas encadenadas, dicen bastante más. */}
          <span className={`${styles.statValue} tabular`}>
            {practicando ? state.score : state.round}
          </span>
          <span className={styles.statLabel}>{practicando ? 'Puntos' : 'Última ronda'}</span>
        </div>
      </div>

      <button className={styles.primaryButton} onClick={restart}>
        {practicando ? 'OTRA SESIÓN' : 'OTRA VEZ'}
      </button>
      <button className={styles.secondaryButton} onClick={home}>
        Inicio
      </button>

      <p className={styles.keyHint}>
        <kbd>Espacio</kbd> para volver a jugar
      </p>
    </div>
  )
}
