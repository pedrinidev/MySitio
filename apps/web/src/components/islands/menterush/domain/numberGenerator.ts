import { createRound, type GameRound } from './round'
import { randomIndex, type RandomSource } from './random'
import type { RoundConfig, ValueRange } from './types'

/**
 * Genera la secuencia de una ronda. Puerto de `NumberGenerator.kt`, con las
 * reglas propias de MenteRush.
 *
 * Reglas heredadas de MentePro:
 * - Nunca sale el 0.
 * - Ningún número es igual al inmediatamente anterior.
 *
 * Reglas nuevas:
 * - El primer número sale de `config.first`: siempre positivo y alto.
 * - **La suma parcial nunca baja de 0.** Como consecuencia el total tampoco es
 *   nunca negativo, así que el jugador no necesita teclear el signo menos.
 */
export function generateRound(
  config: RoundConfig,
  random: RandomSource = Math.random,
): GameRound {
  const pool = [...expand(config.positive), ...(config.negative ? expand(config.negative) : [])]
  const firstPool = expand(config.first)

  if (pool.length < 2 || firstPool.length === 0) {
    // Los rangos válidos del juego nunca llegan aquí.
    throw new Error(`Rango insuficiente: ${pool.length} candidatos disponibles`)
  }

  const numbers: number[] = []
  let previous: number | null = null
  let runningTotal = 0

  for (let i = 0; i < config.quantity; i++) {
    const candidates =
      i === 0 ? firstPool : pool.filter((n) => n !== previous && runningTotal + n >= 0)

    if (candidates.length === 0) {
      // Defensa: siempre queda algún positivo distinto del anterior.
      throw new Error(`Sin candidatos válidos con suma parcial ${runningTotal}`)
    }

    const picked = candidates[randomIndex(random, candidates.length)] as number
    numbers.push(picked)
    runningTotal += picked
    previous = picked
  }

  return createRound(numbers)
}

/** Todos los enteros de un rango, excluido el 0. */
function expand(range: ValueRange): number[] {
  const values: number[] = []
  for (let n = range.min; n <= range.max; n++) {
    if (n !== 0) values.push(n)
  }
  return values
}
