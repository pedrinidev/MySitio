import { useEffect } from 'react'
import type { GameEngine } from '../../application'
import { PRACTICE } from '../../domain'
import { accuracyOf } from '../../data'
import styles from './screens.module.css'

/** La app original de la que nace MenteRush. */
const MENTEPRO_URL =
  'https://play.google.com/store/apps/details?id=com.pedrini.mentepro&hl=es_BO'

/** Menú: modo de operación, récords y arranque. */
export function HomeScreen({ engine }: { engine: GameEngine }) {
  const {
    settings,
    stats,
    setMode,
    setDigits,
    setPlay,
    setLevel,
    toggleSound,
    toggleHaptics,
    start,
  } = engine

  const practicando = settings.play === 'PRACTICA'

  // Empezar sin tocar el ratón, igual que se juega.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault()
        start()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [start])

  return (
    <div className={styles.screen}>

      <div>
        <h1 className={styles.title}>
          Mente<span className={styles.titleAccent}>Rush</span>
        </h1>
        <p className={styles.tagline}>
          {practicando
            ? 'Aparecen números uno a uno y los vas sumando de cabeza. Al final escribes el resultado. Equivocarse no quita nada.'
            : 'Suma de cabeza los números que aparecen. Encadena aciertos, multiplica la puntuación y aguanta lo que puedas: tienes tres vidas.'}
        </p>
      </div>

      <div>
        <div className={styles.modeSwitch} role="group" aria-label="Cómo jugar">
          <button
            className={`${styles.modeOption} ${practicando ? styles.selected : ''}`}
            onClick={() => setPlay('PRACTICA')}
            aria-pressed={practicando}
          >
            Práctica
          </button>
          <button
            className={`${styles.modeOption} ${!practicando ? styles.selected : ''}`}
            onClick={() => setPlay('RETO')}
            aria-pressed={!practicando}
          >
            Reto
          </button>
        </div>
        <p className={styles.modeHint}>
          {practicando
            ? 'Para primaria: 10 rondas, sin vidas y sin prisa.'
            : 'Tres vidas y a aguantar lo que puedas.'}
        </p>
      </div>

      {practicando ? (
        <div>
          <div className={styles.modeSwitch} role="group" aria-label="Tramo escolar">
            {(['INICIAL', 'MEDIO', 'AVANZADO'] as const).map((nivel) => (
              <button
                key={nivel}
                className={`${styles.modeOption} ${settings.level === nivel ? styles.selected : ''}`}
                onClick={() => setLevel(nivel)}
                aria-pressed={settings.level === nivel}
              >
                {PRACTICE[nivel].grades}
              </button>
            ))}
          </div>
          <p className={styles.modeHint}>
            {PRACTICE[settings.level].quantity} números del 1 al {PRACTICE[settings.level].max},{' '}
            {(PRACTICE[settings.level].delayMs / 1000).toFixed(1)} s cada uno.
          </p>
        </div>
      ) : (
        <>
      <div>
        <div className={styles.modeSwitch} role="group" aria-label="Modo de operación">
          <button
            className={`${styles.modeOption} ${settings.mode === 'SUMA' ? styles.selected : ''}`}
            onClick={() => setMode('SUMA')}
            aria-pressed={settings.mode === 'SUMA'}
          >
            Suma
          </button>
          <button
            className={`${styles.modeOption} ${settings.mode === 'MIXTO' ? styles.selected : ''}`}
            onClick={() => setMode('MIXTO')}
            aria-pressed={settings.mode === 'MIXTO'}
          >
            Mixto
          </button>
        </div>
        <p className={styles.modeHint}>
          {settings.mode === 'SUMA'
            ? 'Solo números positivos.'
            : 'Con negativos: también hay que restar.'}
        </p>
      </div>

      <div>
        <div className={styles.modeSwitch} role="group" aria-label="Tamaño de los números">
          <button
            className={`${styles.modeOption} ${settings.digits === 'ONE' ? styles.selected : ''}`}
            onClick={() => setDigits('ONE')}
            aria-pressed={settings.digits === 'ONE'}
          >
            1 cifra
          </button>
          <button
            className={`${styles.modeOption} ${settings.digits === 'TWO' ? styles.selected : ''}`}
            onClick={() => setDigits('TWO')}
            aria-pressed={settings.digits === 'TWO'}
          >
            2 cifras
          </button>
        </div>
        <p className={styles.modeHint}>
          {settings.digits === 'ONE'
            ? 'Números del 1 al 9.'
            : 'Empieza hasta 20 y va creciendo hasta 99.'}
        </p>
      </div>
        </>
      )}

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <span className={`${styles.statValue} tabular`}>{stats.record}</span>
          <span className={styles.statLabel}>Récord</span>
        </div>
        <div className={styles.statCard}>
          <span className={`${styles.statValue} tabular`}>{stats.bestCombo}</span>
          <span className={styles.statLabel}>Mejor racha</span>
        </div>
        <div className={styles.statCard}>
          <span className={`${styles.statValue} tabular`}>{stats.gamesPlayed}</span>
          <span className={styles.statLabel}>Partidas</span>
        </div>
        <div className={styles.statCard}>
          <span className={`${styles.statValue} tabular`}>{accuracyOf(stats)}%</span>
          <span className={styles.statLabel}>Precisión</span>
        </div>
      </div>

      <button className={styles.primaryButton} onClick={start}>
        JUGAR
      </button>

      <div className={styles.toggles}>
        <button
          className={`${styles.toggle} ${settings.sound ? styles.on : ''}`}
          onClick={toggleSound}
          aria-pressed={settings.sound}
        >
          {settings.sound ? '🔊 Sonido' : '🔇 Sonido'}
        </button>
        <button
          className={`${styles.toggle} ${settings.haptics ? styles.on : ''}`}
          onClick={toggleHaptics}
          aria-pressed={settings.haptics}
        >
          {settings.haptics ? '📳 Vibración' : '📴 Vibración'}
        </button>
      </div>

      <p className={styles.keyHint}>
        <kbd>Espacio</kbd> para empezar · números y <kbd>Enter</kbd> para responder
      </p>

      <a
        className={styles.storeLink}
        href={MENTEPRO_URL}
        target="_blank"
        rel="noopener noreferrer"
      >
        <span aria-hidden="true">📱</span> Descarga <strong>MentePro</strong> para Android
      </a>
    </div>
  )
}
