import { useEffect, useRef, useState } from 'react'
import { INITIAL_LIVES, TIMING } from '../../domain'
import { useKeypad, type GameEngine } from '../../application'
import { AnswerDisplay } from '../components/AnswerDisplay'
import { BigNumber } from '../components/BigNumber'
import { ComboMeter } from '../components/ComboMeter'
import { Keypad } from '../components/Keypad'
import { LivesIndicator } from '../components/LivesIndicator'
import { ScoreCounter } from '../components/ScoreCounter'
import { TimerBar } from '../components/TimerBar'
import { ComboVignette, ParticleCanvas, ScreenFlash } from '../effects'
import effects from '../effects/effects.module.css'
import styles from './screens.module.css'

/** A partir de este tier la pantalla late por sí sola. */
const VIGNETTE_TIER = 3

export function GameScreen({ engine }: { engine: GameEngine }) {
  const { state, tier, multiplier, answerRemainingMs, visibleNumber, submit, home } = engine

  const keypad = useKeypad({
    active: state.status === 'answering',
    onSubmit: submit,
    // Acertar se reconoce solo; solo hay que confirmar para fallar.
    autoSubmitValue: state.status === 'answering' ? state.total : null,
  })

  // El color de las partículas se lee del CSS para no duplicar la paleta de tiers.
  const rootRef = useRef<HTMLDivElement>(null)
  const [accent, setAccent] = useState('#4d8dff')
  useEffect(() => {
    const element = rootRef.current
    if (!element) return
    const value = getComputedStyle(element).getPropertyValue('--accent').trim()
    if (value) setAccent(value)
  }, [tier])

  const wrong = state.lastOutcome !== null && state.lastOutcome !== 'correct'
  const showingFeedback = state.status === 'feedback'
  const countdownStep = 3 - Math.floor(state.elapsedMs / (TIMING.COUNTDOWN_MS / 3))

  return (
    <div
      ref={rootRef}
      className={[
        styles.screen,
        styles.game,
        showingFeedback && wrong ? effects.slowmo : '',
        showingFeedback && wrong ? effects.shake : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <header className={styles.hud}>
        <div className={styles.hudBlock}>
          <span className={styles.hudLabel}>
            {/* En práctica la sesión tiene final conocido; en reto, vidas. */}
            {state.roundLimit ? `Ronda ${state.round} de ${state.roundLimit}` : `Ronda ${state.round}`}
          </span>
          {state.roundLimit === null && (
            <LivesIndicator lives={state.lives} total={INITIAL_LIVES} />
          )}
        </div>

        <ComboMeter combo={state.combo} multiplier={multiplier} />

        <div className={`${styles.hudBlock} ${styles.right}`}>
          <span className={styles.hudLabel}>Puntos</span>
          <ScoreCounter value={state.score} />
        </div>
      </header>

      <div className={styles.stage}>
        {state.status === 'countdown' && (
          <div key={countdownStep} className={`${styles.countdownNumber} tabular`}>
            {Math.max(countdownStep, 1)}
          </div>
        )}

        {state.status === 'showing' &&
          (visibleNumber !== null ? (
            <BigNumber key={state.visibleIndex} value={visibleNumber} />
          ) : (
            <span className={styles.prompt}>…</span>
          ))}

        {state.status === 'answering' && (
          <>
            <span className={styles.prompt}>¿Cuánto suma?</span>
            <AnswerDisplay raw={keypad.raw} />
          </>
        )}

        {showingFeedback && (
          <div className={styles.feedback}>
            <div
              className={`${styles.feedbackMark} ${
                wrong ? styles.feedbackWrong : styles.feedbackCorrect
              }`}
            >
              {wrong ? '✕' : '✓'}
            </div>
            {wrong ? (
              <span className={styles.feedbackDetail}>
                {state.lastOutcome === 'timeout'
                  ? `Se acabó el tiempo · era ${state.total}`
                  : `Era ${state.total}, no ${state.lastAnswer}`}
              </span>
            ) : (
              <>
                <span className={`${styles.feedbackGain} tabular`}>+{state.lastGain}</span>
                {multiplier > 1 && (
                  <span className={styles.feedbackDetail}>racha ×{multiplier}</span>
                )}
              </>
            )}
            {state.isNewRecord && <span className={styles.recordBanner}>¡Nuevo récord!</span>}
          </div>
        )}
      </div>

      <footer className={styles.footer}>
        {state.status === 'answering' && (
          <>
            <TimerBar remainingMs={answerRemainingMs} totalMs={state.config.answerMs} />
            <Keypad keypad={keypad} />
          </>
        )}
        <button className={styles.quitButton} onClick={home}>
          Salir
        </button>
      </footer>

      {/* Efectos: se remontan con una key nueva en cada resolución. */}
      {showingFeedback && (
        <ScreenFlash key={state.totalAnswers} variant={wrong ? 'wrong' : 'correct'} />
      )}
      <ParticleCanvas burstKey={state.correctAnswers} color={accent} intensity={tier} />
      {tier >= VIGNETTE_TIER && <ComboVignette />}
    </div>
  )
}
