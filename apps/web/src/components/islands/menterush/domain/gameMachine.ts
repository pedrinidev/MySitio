import { PRACTICE_ROUNDS, configForPractice, configForRound } from './difficulty'
import { generateRound } from './numberGenerator'
import { pointsFor } from './scoring'
import type { RandomSource } from './random'
import type {
  Action,
  AnswerOutcome,
  DigitMode,
  GameState,
  OperationMode,
  PlayMode,
  SchoolLevel,
} from './types'

/**
 * Máquina de estados de la partida, como reducer puro.
 *
 * El tiempo entra exclusivamente por la acción `TICK`, nunca se consulta un
 * reloj real: una partida completa se puede simular en un test sin esperar un
 * solo milisegundo. El azar entra por `RandomSource`, inyectado al crear el
 * reducer.
 *
 * ```
 * idle → countdown → showing → answering → feedback ─┬→ showing   (quedan vidas)
 *                                                     └→ gameOver  (0 vidas)
 * ```
 *
 * No existe una acción `TIMEOUT`: agotar la ventana de respuesta es simplemente
 * el `TICK` que rebasa `answerMs`, lo que evita que UI y dominio puedan
 * discrepar sobre cuándo se acabó el tiempo.
 */

export const TIMING = {
  /** Cuenta atrás inicial: 3 × 700 ms. */
  COUNTDOWN_MS: 2100,
  /**
   * Respiro en negro al empezar cada ronda, antes del primer número. Sin él la
   * ronda siguiente arranca encima del feedback y no da tiempo a concentrarse.
   */
  PRE_ROUND_PAUSE_MS: 600,
  /** Pausa en negro entre el último número y la petición de respuesta. */
  PRE_ANSWER_PAUSE_MS: 250,
  FEEDBACK_CORRECT_MS: 450,
  /** Más largo: incluye la cámara lenta del fallo. */
  FEEDBACK_WRONG_MS: 900,
} as const

export const INITIAL_LIVES = 3

/** Estado de arranque, en el menú y sin partida en curso. */
export function createInitialState(
  mode: OperationMode,
  record = 0,
  digits: DigitMode = 'ONE',
  play: PlayMode = 'RETO',
  level: SchoolLevel = 'MEDIO',
): GameState {
  return {
    status: 'idle',
    mode,
    digits,
    play,
    level,
    roundLimit: play === 'PRACTICA' ? PRACTICE_ROUNDS : null,
    round: 0,
    config: configFor(1, mode, digits, play, level),
    sequence: [],
    total: 0,
    visibleIndex: -1,
    elapsedMs: 0,
    phaseDurationMs: 0,
    lives: INITIAL_LIVES,
    score: 0,
    combo: 0,
    bestCombo: 0,
    roundsCleared: 0,
    correctAnswers: 0,
    totalAnswers: 0,
    lastOutcome: null,
    lastAnswer: null,
    lastGain: 0,
    record,
    isNewRecord: false,
  }
}

/** Arranca la cuenta atrás conservando modo y récord. */
/** Elige la tabla de dificultad según cómo se esté jugando. */
function configFor(
  round: number,
  mode: OperationMode,
  digits: DigitMode,
  play: PlayMode,
  level: SchoolLevel,
) {
  return play === 'PRACTICA' ? configForPractice(level) : configForRound(round, mode, digits)
}

function startCountdown(state: GameState): GameState {
  return {
    ...createInitialState(state.mode, state.record, state.digits, state.play, state.level),
    status: 'countdown',
    phaseDurationMs: TIMING.COUNTDOWN_MS,
  }
}

/** Prepara y entra en la ronda indicada. `carryMs` es el sobrante del tick. */
function startRound(state: GameState, round: number, random: RandomSource, carryMs: number): GameState {
  const config = configFor(round, state.mode, state.digits, state.play, state.level)
  const generated = generateRound(config, random)

  return {
    ...state,
    status: 'showing',
    round,
    config,
    sequence: generated.numbers,
    total: generated.total,
    // Arranca en negro: el primer número llega tras el respiro.
    visibleIndex: -1,
    elapsedMs: carryMs,
    phaseDurationMs:
      TIMING.PRE_ROUND_PAUSE_MS +
      config.quantity * config.delayMs +
      TIMING.PRE_ANSWER_PAUSE_MS,
    lastOutcome: null,
    lastAnswer: null,
    lastGain: 0,
  }
}

/**
 * Resuelve la respuesta del jugador (o su ausencia) y entra en `feedback`.
 * Aquí se actualizan puntuación, combo, vidas y la marca de récord.
 */
function resolveAnswer(
  state: GameState,
  outcome: AnswerOutcome,
  value: number | null,
  timeLeftMs: number,
): GameState {
  const correct = outcome === 'correct'
  const combo = correct ? state.combo + 1 : 0
  const gained = correct
    ? pointsFor({
        quantity: state.config.quantity,
        combo,
        timeLeftMs,
        answerMs: state.config.answerMs,
      })
    : 0
  const score = state.score + gained

  return {
    ...state,
    status: 'feedback',
    visibleIndex: -1,
    elapsedMs: 0,
    phaseDurationMs: correct ? TIMING.FEEDBACK_CORRECT_MS : TIMING.FEEDBACK_WRONG_MS,
    // En práctica no se pierden vidas: fallar enseña el resultado y se sigue.
    lives: correct || state.play === 'PRACTICA' ? state.lives : state.lives - 1,
    score,
    combo,
    bestCombo: Math.max(state.bestCombo, combo),
    roundsCleared: correct ? state.roundsCleared + 1 : state.roundsCleared,
    correctAnswers: correct ? state.correctAnswers + 1 : state.correctAnswers,
    totalAnswers: state.totalAnswers + 1,
    lastOutcome: outcome,
    lastAnswer: value,
    lastGain: gained,
    // Se marca en cuanto se supera, para poder celebrarlo en mitad de la partida.
    isNewRecord: state.isNewRecord || score > state.record,
  }
}

function toGameOver(state: GameState): GameState {
  return { ...state, status: 'gameOver', visibleIndex: -1, elapsedMs: 0, phaseDurationMs: 0 }
}

/**
 * Índice del número visible dentro de la fase `showing`, o -1 mientras la
 * pantalla está en negro: durante el respiro inicial y en la pausa final.
 */
function visibleIndexAt(elapsedMs: number, quantity: number, delayMs: number): number {
  const sinceFirst = elapsedMs - TIMING.PRE_ROUND_PAUSE_MS
  if (sinceFirst < 0) return -1
  const index = Math.floor(sinceFirst / delayMs)
  return index >= quantity ? -1 : index
}

function tick(state: GameState, deltaMs: number, random: RandomSource): GameState {
  if (deltaMs <= 0) return state

  const elapsed = state.elapsedMs + deltaMs
  const overflow = elapsed - state.phaseDurationMs

  switch (state.status) {
    case 'countdown':
      return overflow >= 0 ? startRound(state, 1, random, overflow) : { ...state, elapsedMs: elapsed }

    case 'showing':
      if (overflow >= 0) {
        return {
          ...state,
          status: 'answering',
          visibleIndex: -1,
          elapsedMs: overflow,
          phaseDurationMs: state.config.answerMs,
        }
      }
      return {
        ...state,
        elapsedMs: elapsed,
        visibleIndex: visibleIndexAt(elapsed, state.config.quantity, state.config.delayMs),
      }

    case 'answering':
      // Rebasar la ventana es el timeout: cuesta una vida y rompe el combo.
      return overflow >= 0
        ? resolveAnswer(state, 'timeout', null, 0)
        : { ...state, elapsedMs: elapsed }

    case 'feedback': {
      if (overflow < 0) return { ...state, elapsedMs: elapsed }
      // La práctica termina al completar la sesión; el reto, al quedarse sin vidas.
      const sessionOver = state.roundLimit !== null && state.round >= state.roundLimit
      return state.lives > 0 && !sessionOver
        ? startRound(state, state.round + 1, random, overflow)
        : toGameOver(state)
    }

    // `idle` y `gameOver` no consumen tiempo.
    default:
      return state
  }
}

/**
 * Crea el reducer de la partida con una fuente de azar concreta.
 * Las acciones inválidas para la fase actual se ignoran devolviendo el estado.
 */
export function createGameReducer(random: RandomSource = Math.random) {
  return function gameReducer(state: GameState, action: Action): GameState {
    switch (action.type) {
      case 'START':
        if (state.status !== 'idle') return state
        return startCountdown({
          ...state,
          mode: action.mode,
          digits: action.digits,
          play: action.play,
          level: action.level,
          record: action.record,
        })

      case 'RESTART':
        if (state.status !== 'gameOver') return state
        // El récord se actualiza con lo logrado, para que la siguiente partida
        // compare contra la marca real.
        return startCountdown({ ...state, record: Math.max(state.record, state.score) })

      case 'HOME':
        return createInitialState(
          state.mode,
          Math.max(state.record, state.score),
          state.digits,
          state.play,
          state.level,
        )

      case 'TICK':
        return tick(state, action.deltaMs, random)

      case 'SUBMIT': {
        if (state.status !== 'answering') return state
        const timeLeftMs = Math.max(0, state.config.answerMs - state.elapsedMs)
        const outcome: AnswerOutcome = action.value === state.total ? 'correct' : 'wrong'
        return resolveAnswer(state, outcome, action.value, timeLeftMs)
      }

      default:
        return state
    }
  }
}
