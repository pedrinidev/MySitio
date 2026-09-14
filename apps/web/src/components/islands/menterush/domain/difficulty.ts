import type { DigitMode, OperationMode, RoundConfig, SchoolLevel, ValueRange } from './types'

/**
 * Curva de dificultad continua. Es la única fuente de verdad del balance del
 * juego: sustituye a la tabla de 5 niveles fijos de MentePro (`GameConfig.kt`).
 *
 * El progreso se mide como `r - 1`, de forma que la ronda 1 arranca exactamente
 * en los valores más suaves.
 */
export const DIFFICULTY = {
  /** Números en la primera ronda. */
  BASE_QUANTITY: 3,
  MAX_QUANTITY: 12,
  /** Con dos cifras cada número cuesta mucho más: la ronda se corta antes. */
  MAX_QUANTITY_TWO_DIGITS: 8,

  /**
   * En dos cifras los números no empiezan siendo grandes: arrancan en 1..20
   * (incluidos los de una cifra) durante las primeras rondas y el techo sube
   * desde ahí. Empezar directamente en 10..99 era un muro desde el primer número.
   */
  TWO_START_MAX: 20,
  TWO_EASY_ROUNDS: 4,
  TWO_MAX_STEP: 10,
  TWO_FINAL_MAX: 99,
  /** Se añade un número cada 3 rondas. */
  ROUNDS_PER_EXTRA_NUMBER: 3,

  /** Tiempo en pantalla de cada número, ronda 1. */
  BASE_DELAY_MS: 1400,
  MIN_DELAY_MS: 320,
  /** Con dos cifras hace falta más tiempo para leer y sumar. */
  BASE_DELAY_MS_TWO_DIGITS: 1900,
  MIN_DELAY_MS_TWO_DIGITS: 520,

  /** Ventana de respuesta, ronda 1. */
  BASE_ANSWER_MS: 5000,
  MIN_ANSWER_MS: 2500,
  BASE_ANSWER_MS_TWO_DIGITS: 6500,
  MIN_ANSWER_MS_TWO_DIGITS: 3200,

  /**
   * Rondas iniciales que se juegan a la velocidad base, sin acelerar nada.
   * Sirven para entrar en calor antes de que empiece la cuesta.
   */
  GRACE_ROUNDS: 3,
  /**
   * Cuánto se acelera cada ronda, en tanto por uno del valor anterior.
   *
   * Es un porcentaje y no una cantidad fija de milisegundos a propósito: así la
   * aceleración se percibe **igual de suave en toda la partida**. Restar 50 ms a
   * 1400 no se nota, pero restárselos a 400 es un frenazo; quitar siempre un 4%
   * se siente igual en los dos casos, y el mínimo se alcanza asintóticamente,
   * sin el escalón de quedarse plano de golpe.
   */
  SPEED_DECAY: 0.04,
  /** La ventana de respuesta se estrecha más despacio: agobia más perderla. */
  ANSWER_DECAY: 0.025,
} as const

interface Ranges {
  positive: ValueRange
  negative: ValueRange
  first: ValueRange
}

/** Una cifra: rangos fijos, no hay margen para escalar. */
const ONE_DIGIT_RANGES: Ranges = {
  positive: { min: 1, max: 9 },
  negative: { min: -4, max: -1 },
  first: { min: 5, max: 9 },
}

/**
 * Rangos de la ronda. Con dos cifras el techo crece con el progreso: las
 * primeras rondas se juegan con números hasta 20 y solo más tarde aparecen los
 * de 90. Los negativos llegan hasta la mitad del techo y el primer número sale
 * siempre de la mitad alta.
 */
function rangesFor(digits: DigitMode, progress: number): Ranges {
  if (digits === 'ONE') return ONE_DIGIT_RANGES

  const stepsTaken = Math.max(0, progress - (DIFFICULTY.TWO_EASY_ROUNDS - 1))
  const max = Math.min(
    DIFFICULTY.TWO_FINAL_MAX,
    DIFFICULTY.TWO_START_MAX + stepsTaken * DIFFICULTY.TWO_MAX_STEP,
  )

  return {
    positive: { min: 1, max },
    negative: { min: -Math.floor(max / 2), max: -1 },
    first: { min: Math.ceil(max / 2), max },
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

/**
 * Rampa de velocidad: las primeras `GRACE_ROUNDS` rondas mantienen el valor base
 * y a partir de ahí cada ronda es un `decay` más rápida que la anterior, sin
 * bajar nunca del mínimo.
 */
function ramp(base: number, min: number, progress: number, decay: number): number {
  const accelerating = Math.max(0, progress - (DIFFICULTY.GRACE_ROUNDS - 1))
  return Math.max(min, Math.round(base * Math.pow(1 - decay, accelerating)))
}

/**
 * Configuración de la ronda `round` (1-based) para el modo y el tamaño de
 * número dados.
 *
 * Rondas fuera de rango se tratan como la ronda 1: la función nunca falla, para
 * que un estado corrupto no pueda romper una partida en curso.
 */
export function configForRound(
  round: number,
  mode: OperationMode,
  digits: DigitMode = 'ONE',
): RoundConfig {
  const progress = Math.max(0, Math.floor(round) - 1)
  const two = digits === 'TWO'
  const ranges = rangesFor(digits, progress)

  const quantity = clamp(
    DIFFICULTY.BASE_QUANTITY + Math.floor(progress / DIFFICULTY.ROUNDS_PER_EXTRA_NUMBER),
    DIFFICULTY.BASE_QUANTITY,
    two ? DIFFICULTY.MAX_QUANTITY_TWO_DIGITS : DIFFICULTY.MAX_QUANTITY,
  )

  const delayMs = ramp(
    two ? DIFFICULTY.BASE_DELAY_MS_TWO_DIGITS : DIFFICULTY.BASE_DELAY_MS,
    two ? DIFFICULTY.MIN_DELAY_MS_TWO_DIGITS : DIFFICULTY.MIN_DELAY_MS,
    progress,
    DIFFICULTY.SPEED_DECAY,
  )

  const answerMs = ramp(
    two ? DIFFICULTY.BASE_ANSWER_MS_TWO_DIGITS : DIFFICULTY.BASE_ANSWER_MS,
    two ? DIFFICULTY.MIN_ANSWER_MS_TWO_DIGITS : DIFFICULTY.MIN_ANSWER_MS,
    progress,
    DIFFICULTY.ANSWER_DECAY,
  )

  return {
    quantity,
    delayMs,
    answerMs,
    positive: ranges.positive,
    negative: mode === 'MIXTO' ? ranges.negative : null,
    first: ranges.first,
  }
}

/**
 * Configuración del modo práctica, pensado para primaria.
 *
 * Tres diferencias de fondo con el modo Reto:
 * - **Velocidad constante**: no acelera dentro de la sesión. Un ritmo estable
 *   deja al niño encontrar su método; la progresión viene de cambiar de tramo.
 * - **Mucho más tiempo por número**: el cuello de botella a esa edad no es la
 *   suma, es sostener el total en la memoria de trabajo mientras llega el
 *   siguiente número.
 * - **Sin negativos ni dos cifras**: los números negativos no se ven en primaria,
 *   y `-4` en pantalla es notación de número negativo, no una resta.
 */
export const PRACTICE: Record<
  SchoolLevel,
  { quantity: number; delayMs: number; answerMs: number; max: number; grades: string }
> = {
  INICIAL: { quantity: 3, delayMs: 3000, answerMs: 8000, max: 5, grades: '1º y 2º' },
  MEDIO: { quantity: 4, delayMs: 2500, answerMs: 7000, max: 9, grades: '3º y 4º' },
  AVANZADO: { quantity: 5, delayMs: 2000, answerMs: 6000, max: 9, grades: '5º y 6º' },
}

/** Rondas que dura una sesión de práctica antes del resumen. */
export const PRACTICE_ROUNDS = 10

/**
 * Configuración de una ronda de práctica. No depende del número de ronda: todas
 * son iguales dentro de la sesión.
 */
export function configForPractice(level: SchoolLevel): RoundConfig {
  const preset = PRACTICE[level]
  const range: ValueRange = { min: 1, max: preset.max }

  return {
    quantity: preset.quantity,
    delayMs: preset.delayMs,
    answerMs: preset.answerMs,
    positive: range,
    negative: null,
    first: range,
  }
}
