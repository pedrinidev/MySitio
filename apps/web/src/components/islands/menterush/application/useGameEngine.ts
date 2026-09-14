import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import {
  TIMING,
  createGameReducer,
  createInitialState,
  multiplierFor,
  tierFor,
  type DigitMode,
  type GameState,
  type OperationMode,
  type PlayMode,
  type SchoolLevel,
} from '../domain'
import {
  createSettingsRepository,
  createStatsRepository,
  getSafeStorage,
  type Settings,
  type Stats,
  type StatsByMode,
} from '../data'
import { useAudio } from './useAudio'
import { useCountdown } from './useCountdown'
import { useHaptics } from './useHaptics'
import { useTheme, type ResolvedTheme } from './useTheme'

/** Estados en los que el reloj del juego debe correr. */
const RUNNING: ReadonlySet<GameState['status']> = new Set([
  'countdown',
  'showing',
  'answering',
  'feedback',
])

export interface GameEngine {
  readonly state: GameState
  readonly stats: Stats
  readonly settings: Settings
  /** Tier de combo actual (0-4): gobierna color, sonido e intensidad. */
  readonly tier: number
  readonly multiplier: number
  /** Progreso de la fase actual, 0..1. */
  readonly phaseProgress: number
  /** Milisegundos que quedan para responder. */
  readonly answerRemainingMs: number
  /** Número visible ahora mismo, o `null`. */
  readonly visibleNumber: number | null
  /** Tema realmente aplicado, ya resuelto si la preferencia es `auto`. */
  readonly theme: ResolvedTheme
  start(): void
  restart(): void
  home(): void
  submit(value: number): void
  setMode(mode: OperationMode): void
  setDigits(digits: DigitMode): void
  setPlay(play: PlayMode): void
  setLevel(level: SchoolLevel): void
  toggleSound(): void
  toggleHaptics(): void
  toggleTheme(): void
}

/**
 * Orquestador de la partida: une el reducer del dominio con el reloj real, el
 * sonido, la vibración y la persistencia. Es la única pieza que conoce las
 * cuatro capas a la vez.
 */
export function useGameEngine(): GameEngine {
  const storage = useMemo(() => getSafeStorage(), [])
  const statsRepo = useMemo(() => createStatsRepository(storage), [storage])
  const settingsRepo = useMemo(() => createSettingsRepository(storage), [storage])

  const [settings, setSettings] = useState<Settings>(() => settingsRepo.load())
  // Las estadísticas van por modo: se guardan las dos y se muestra la del modo activo.
  const [statsByMode, setStatsByMode] = useState<StatsByMode>(() => statsRepo.loadAll())
  const stats: Stats = statsByMode[settings.play]

  const reducer = useMemo(() => createGameReducer(), [])
  const [state, dispatch] = useReducer(
    reducer,
    null,
    () => {
      const saved = settingsRepo.load()
      return createInitialState(
        saved.mode,
        statsRepo.load(saved.play).record,
        saved.digits,
        saved.play,
        saved.level,
      )
    },
  )

  const audio = useAudio(settings.sound)
  const haptics = useHaptics(settings.haptics)
  const theme = useTheme(settings.theme)

  const running = RUNNING.has(state.status)
  useCountdown(running, (deltaMs) => dispatch({ type: 'TICK', deltaMs }))

  // ---- Efectos sensoriales -------------------------------------------------

  // Un sonido por número, con el pitch subiendo a lo largo de la secuencia.
  const lastNoteRef = useRef(-1)
  useEffect(() => {
    if (state.status !== 'showing' || state.visibleIndex < 0) {
      lastNoteRef.current = -1
      return
    }
    if (state.visibleIndex === lastNoteRef.current) return
    lastNoteRef.current = state.visibleIndex
    audio.note(state.visibleIndex, state.sequence.length)
    haptics.light()
  }, [state.status, state.visibleIndex, state.sequence.length, audio, haptics])

  // Beeps de la cuenta atrás: uno por cada 700 ms.
  const lastBeepRef = useRef(-1)
  useEffect(() => {
    if (state.status !== 'countdown') {
      lastBeepRef.current = -1
      return
    }
    const step = Math.floor(state.elapsedMs / (TIMING.COUNTDOWN_MS / 3))
    if (step === lastBeepRef.current || step > 2) return
    lastBeepRef.current = step
    audio.countdown(step)
  }, [state.status, state.elapsedMs, audio])

  // Feedback de acierto o fallo, una sola vez por resolución.
  const lastFeedbackRef = useRef(0)
  useEffect(() => {
    if (state.status !== 'feedback') return
    if (lastFeedbackRef.current === state.totalAnswers) return
    lastFeedbackRef.current = state.totalAnswers

    if (state.lastOutcome === 'correct') {
      audio.correct(tierFor(state.combo))
      haptics.success()
    } else {
      audio.wrong()
      haptics.error()
    }
  }, [state.status, state.totalAnswers, state.lastOutcome, state.combo, audio, haptics])

  // El récord se celebra en el momento en que se supera, no al final.
  const recordCelebratedRef = useRef(false)
  useEffect(() => {
    if (!state.isNewRecord) {
      recordCelebratedRef.current = false
      return
    }
    if (recordCelebratedRef.current) return
    recordCelebratedRef.current = true
    audio.record()
  }, [state.isNewRecord, audio])

  // Fin de partida: se persiste una única vez.
  const savedGameRef = useRef(false)
  useEffect(() => {
    if (state.status !== 'gameOver') {
      savedGameRef.current = false
      return
    }
    if (savedGameRef.current) return
    savedGameRef.current = true

    // Se acumula en el modo con el que se jugó, no en el que esté seleccionado ahora.
    statsRepo.registerGame(state.play, {
      score: state.score,
      bestCombo: state.bestCombo,
      correctAnswers: state.correctAnswers,
      totalAnswers: state.totalAnswers,
    })
    setStatsByMode(statsRepo.loadAll())
    audio.gameOver()
    haptics.gameOver()
  }, [
    state.status,
    state.play,
    state.score,
    state.bestCombo,
    state.correctAnswers,
    state.totalAnswers,
    statsRepo,
    audio,
    haptics,
  ])

  // ---- Acciones ------------------------------------------------------------

  const start = useCallback(() => {
    // Debe ocurrir dentro del gesto del usuario para que el navegador permita audio.
    audio.unlock()
    dispatch({
      type: 'START',
      mode: settings.mode,
      digits: settings.digits,
      play: settings.play,
      level: settings.level,
      record: statsRepo.load(settings.play).record,
    })
  }, [audio, settings.mode, settings.digits, settings.play, settings.level, statsRepo])

  const restart = useCallback(() => {
    audio.unlock()
    dispatch({ type: 'RESTART' })
  }, [audio])

  const home = useCallback(() => dispatch({ type: 'HOME' }), [])
  const submit = useCallback((value: number) => dispatch({ type: 'SUBMIT', value }), [])

  const persist = useCallback(
    (next: Settings) => {
      setSettings(next)
      settingsRepo.save(next)
    },
    [settingsRepo],
  )

  const setMode = useCallback(
    (mode: OperationMode) => persist({ ...settings, mode }),
    [persist, settings],
  )
  const setDigits = useCallback(
    (digits: DigitMode) => persist({ ...settings, digits }),
    [persist, settings],
  )
  const setPlay = useCallback(
    (play: PlayMode) => persist({ ...settings, play }),
    [persist, settings],
  )
  const setLevel = useCallback(
    (level: SchoolLevel) => persist({ ...settings, level }),
    [persist, settings],
  )
  const toggleSound = useCallback(
    () => persist({ ...settings, sound: !settings.sound }),
    [persist, settings],
  )
  const toggleHaptics = useCallback(
    () => persist({ ...settings, haptics: !settings.haptics }),
    [persist, settings],
  )
  // Alterna sobre el tema que se ve ahora, venga de `auto` o de una elección previa.
  const toggleTheme = useCallback(
    () => persist({ ...settings, theme: theme === 'dark' ? 'light' : 'dark' }),
    [persist, settings, theme],
  )

  // ---- Derivados para la UI ------------------------------------------------

  const phaseProgress =
    state.phaseDurationMs > 0 ? Math.min(state.elapsedMs / state.phaseDurationMs, 1) : 0

  const answerRemainingMs =
    state.status === 'answering' ? Math.max(0, state.config.answerMs - state.elapsedMs) : 0

  const visibleNumber =
    state.status === 'showing' && state.visibleIndex >= 0
      ? state.sequence[state.visibleIndex] ?? null
      : null

  return {
    state,
    stats,
    settings,
    tier: tierFor(state.combo),
    multiplier: multiplierFor(state.combo),
    phaseProgress,
    answerRemainingMs,
    visibleNumber,
    theme,
    start,
    restart,
    home,
    submit,
    setMode,
    setDigits,
    setPlay,
    setLevel,
    toggleSound,
    toggleHaptics,
    toggleTheme,
  }
}
