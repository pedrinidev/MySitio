/** Secuencia de una ronda junto con su suma. Puerto de `GameRound.kt`. */
export interface GameRound {
  readonly numbers: readonly number[]
  readonly total: number
}

/** Crea una ronda calculando la suma de los números dados. */
export function createRound(numbers: readonly number[]): GameRound {
  return {
    numbers,
    total: numbers.reduce((sum, n) => sum + n, 0),
  }
}
