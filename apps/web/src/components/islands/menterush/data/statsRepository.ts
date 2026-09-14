import type { PlayMode } from '../domain'
import { LEGACY_STATS_KEY, STORAGE_KEYS, type StorageLike } from './storageKeys'

/** Estadísticas acumuladas del jugador en este dispositivo, para un modo. */
export interface Stats {
  readonly record: number
  readonly bestCombo: number
  readonly gamesPlayed: number
  readonly correctAnswers: number
  readonly totalAnswers: number
}

export const EMPTY_STATS: Stats = {
  record: 0,
  bestCombo: 0,
  gamesPlayed: 0,
  correctAnswers: 0,
  totalAnswers: 0,
}

/**
 * Las estadísticas van **separadas por modo**: en Práctica los números son más
 * fáciles y hay más tiempo, así que mezclar sus récords con los de Reto haría
 * que ninguno de los dos significara nada.
 */
export type StatsByMode = Record<PlayMode, Stats>

export const EMPTY_STATS_BY_MODE: StatsByMode = {
  RETO: EMPTY_STATS,
  PRACTICA: EMPTY_STATS,
}

/** Resultado de una partida terminada. */
export interface GameResult {
  readonly score: number
  readonly bestCombo: number
  readonly correctAnswers: number
  readonly totalAnswers: number
}

export interface StatsRepository {
  load(play: PlayMode): Stats
  loadAll(): StatsByMode
  save(play: PlayMode, stats: Stats): void
  /** Acumula una partida del modo dado y devuelve sus estadísticas ya guardadas. */
  registerGame(play: PlayMode, result: GameResult): Stats
}

/** Entero no negativo, o el valor por defecto si el dato está corrupto. */
function readCount(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0
    ? Math.floor(value)
    : fallback
}

/** Valida la forma de lo leído: un JSON manipulado no debe romper el juego. */
function parseStats(value: unknown): Stats {
  if (typeof value !== 'object' || value === null) return EMPTY_STATS
  const data = value as Record<string, unknown>
  return {
    record: readCount(data['record'], 0),
    bestCombo: readCount(data['bestCombo'], 0),
    gamesPlayed: readCount(data['gamesPlayed'], 0),
    correctAnswers: readCount(data['correctAnswers'], 0),
    totalAnswers: readCount(data['totalAnswers'], 0),
  }
}

function parseAll(raw: string | null): StatsByMode {
  if (!raw) return EMPTY_STATS_BY_MODE
  try {
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null) return EMPTY_STATS_BY_MODE
    const data = parsed as Record<string, unknown>
    return { RETO: parseStats(data['RETO']), PRACTICA: parseStats(data['PRACTICA']) }
  } catch {
    return EMPTY_STATS_BY_MODE
  }
}

/**
 * Repositorio de estadísticas. Con `storage` nulo funciona en memoria, de forma
 * que la ausencia de almacenamiento nunca impide jugar.
 */
export function createStatsRepository(storage: StorageLike | null): StatsRepository {
  let memory: StatsByMode = EMPTY_STATS_BY_MODE

  const readAll = (): StatsByMode => {
    if (!storage) return memory
    try {
      const current = storage.getItem(STORAGE_KEYS.stats)
      if (current) return parseAll(current)

      // Sin datos nuevos: se rescata el bloque antiguo como estadísticas de Reto.
      const legacy = storage.getItem(LEGACY_STATS_KEY)
      if (!legacy) return EMPTY_STATS_BY_MODE
      const parsed: unknown = JSON.parse(legacy)
      return { RETO: parseStats(parsed), PRACTICA: EMPTY_STATS }
    } catch {
      return EMPTY_STATS_BY_MODE
    }
  }

  const writeAll = (all: StatsByMode): void => {
    memory = all
    if (!storage) return
    try {
      storage.setItem(STORAGE_KEYS.stats, JSON.stringify(all))
    } catch {
      // Cuota llena o escritura denegada: la partida en curso no debe caerse.
    }
  }

  return {
    loadAll: readAll,
    load: (play) => readAll()[play],
    save(play, stats) {
      writeAll({ ...readAll(), [play]: stats })
    },
    registerGame(play, result) {
      const all = readAll()
      const previous = all[play]
      const updated: Stats = {
        record: Math.max(previous.record, result.score),
        bestCombo: Math.max(previous.bestCombo, result.bestCombo),
        gamesPlayed: previous.gamesPlayed + 1,
        correctAnswers: previous.correctAnswers + result.correctAnswers,
        totalAnswers: previous.totalAnswers + result.totalAnswers,
      }
      writeAll({ ...all, [play]: updated })
      return updated
    },
  }
}

/** Precisión acumulada en tanto por ciento (0 si aún no hay respuestas). */
export function accuracyOf(stats: Stats): number {
  if (stats.totalAnswers === 0) return 0
  return Math.round((stats.correctAnswers / stats.totalAnswers) * 100)
}
