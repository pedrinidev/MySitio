/**
 * Tipos compartidos del dominio.
 *
 * Nada en `domain/` importa React, `window`, `localStorage` ni `Date`:
 * el tiempo y el azar entran siempre como parámetros.
 */

/** Modo de operación. Heredado de MentePro. */
export type OperationMode = 'SUMA' | 'MIXTO'

/**
 * Tamaño de los números que se muestran.
 * - `ONE`: una cifra (1..9). El juego clásico.
 * - `TWO`: dos cifras (10..99), para quien ya va sobrado con las unidades.
 */
export type DigitMode = 'ONE' | 'TWO'

/**
 * Cómo se juega.
 * - `RETO`: el juego original. Tres vidas, game over, combos y aceleración.
 * - `PRACTICA`: pensado para primaria. Sesión de rondas fijas, sin vidas ni
 *   game over, a velocidad constante. Fallar no castiga: enseña el resultado
 *   y se sigue.
 */
export type PlayMode = 'RETO' | 'PRACTICA'

/**
 * Tramo escolar del modo práctica. La progresión no ocurre dentro de la sesión
 * sino cambiando de tramo: para un niño es más útil un ritmo estable que una
 * cuesta.
 */
export type SchoolLevel = 'INICIAL' | 'MEDIO' | 'AVANZADO'

/** Rango cerrado de valores permitidos. */
export interface ValueRange {
  readonly min: number
  readonly max: number
}

/** Fase actual de la partida. Ver `gameMachine.ts`. */
export type GameStatus =
  | 'idle'
  | 'countdown'
  | 'showing'
  | 'answering'
  | 'feedback'
  | 'gameOver'

/** Resultado de la última respuesta del jugador. */
export type AnswerOutcome = 'correct' | 'wrong' | 'timeout'

/** Parámetros de una ronda concreta, derivados de la curva de dificultad. */
export interface RoundConfig {
  /** Cuántos números se muestran. */
  readonly quantity: number
  /** Tiempo (ms) que cada número permanece en pantalla. */
  readonly delayMs: number
  /** Ventana (ms) para teclear la respuesta. */
  readonly answerMs: number
  /**
   * Números positivos permitidos. Con una cifra es 1..9; con dos, 10..99.
   * Nunca incluye el 0.
   */
  readonly positive: ValueRange
  /**
   * Números negativos permitidos, o `null` en modo Suma. Son más suaves que los
   * positivos (una cifra: -4..-1; dos cifras: -49..-10) porque restar de cabeza
   * cuesta bastante más que sumar.
   */
  readonly negative: ValueRange | null
  /**
   * Rango del **primer** número de la ronda, siempre positivo y alto: da colchón
   * para que la suma no arranque pegada a cero.
   */
  readonly first: ValueRange
}

/** Acciones que hacen avanzar la máquina de estados. */
export type Action =
  /** Arranca una partida desde el menú. `record` es la mejor puntuación previa. */
  | {
      type: 'START'
      mode: OperationMode
      digits: DigitMode
      play: PlayMode
      level: SchoolLevel
      record: number
    }
  /** Avance del tiempo. Único canal por el que el dominio conoce el reloj. */
  | { type: 'TICK'; deltaMs: number }
  /** El jugador confirma una respuesta. */
  | { type: 'SUBMIT'; value: number }
  /** Reinicio inmediato desde la pantalla de game over. */
  | { type: 'RESTART' }
  /** Vuelta al menú. */
  | { type: 'HOME' }

/** Estado completo de la partida. */
export interface GameState {
  readonly status: GameStatus
  readonly mode: OperationMode
  readonly digits: DigitMode
  readonly play: PlayMode
  readonly level: SchoolLevel
  /** Rondas que dura la sesión de práctica, o `null` si se juega hasta perder. */
  readonly roundLimit: number | null

  /** Ronda actual, 1-based. */
  readonly round: number
  readonly config: RoundConfig
  /** Números de la ronda en curso. */
  readonly sequence: readonly number[]
  /** Suma correcta de `sequence`. */
  readonly total: number
  /** Índice del número visible, o -1 si no hay ninguno en pantalla. */
  readonly visibleIndex: number

  /** Tiempo acumulado dentro de la fase actual. */
  readonly elapsedMs: number
  /** Duración de la fase actual; permite a la UI pintar barras de progreso. */
  readonly phaseDurationMs: number

  readonly lives: number
  readonly score: number
  readonly combo: number
  readonly bestCombo: number
  readonly roundsCleared: number

  /** Respuestas acertadas y totales, para calcular precisión. */
  readonly correctAnswers: number
  readonly totalAnswers: number

  readonly lastOutcome: AnswerOutcome | null
  readonly lastAnswer: number | null
  /** Puntos ganados en la última respuesta. La UI los muestra, no los recalcula. */
  readonly lastGain: number

  /** Récord con el que arrancó la partida. */
  readonly record: number
  /** True en cuanto se supera el récord, en mitad de la partida. */
  readonly isNewRecord: boolean
}
