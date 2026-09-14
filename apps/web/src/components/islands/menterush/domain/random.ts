/**
 * Fuente de aleatoriedad inyectable: devuelve un número en [0, 1).
 *
 * El dominio nunca llama a `Math.random` directamente; así los tests son
 * deterministas y en el futuro se puede sembrar por fecha (reto diario).
 */
export type RandomSource = () => number

/**
 * PRNG mulberry32: rápido, determinista y con buena distribución para el uso
 * que le damos. La misma semilla produce siempre la misma secuencia.
 */
export function createSeededRandom(seed: number): RandomSource {
  let state = seed >>> 0
  return () => {
    state = (state + 0x6d2b79f5) >>> 0
    let t = state
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** Entero en [0, size). */
export function randomIndex(random: RandomSource, size: number): number {
  return Math.floor(random() * size)
}
