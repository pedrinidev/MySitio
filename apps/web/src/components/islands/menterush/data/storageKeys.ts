/**
 * Claves de persistencia, versionadas: subir la versión permite cambiar el
 * formato sin corromper los datos de quien ya jugaba.
 */
export const STORAGE_KEYS = {
  /** v2: las estadísticas pasaron a guardarse por modo de juego. */
  stats: 'menterush.v2.stats',
  settings: 'menterush.v1.settings',
} as const

/**
 * Clave anterior, con un único bloque de estadísticas. Se lee una vez para no
 * perder el récord de quien ya jugaba: aquellas partidas eran todas de Reto.
 */
export const LEGACY_STATS_KEY = 'menterush.v1.stats'

/**
 * Subconjunto de `Storage` que realmente usamos. Permite inyectar un doble en
 * los tests y no depender de `window`.
 */
export interface StorageLike {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
}

/**
 * Devuelve `localStorage` si es utilizable, o `null`.
 *
 * En modo incógnito de algunos navegadores, con cookies bloqueadas o dentro de
 * un iframe restrictivo, el mero acceso lanza. Los repositorios caen entonces a
 * memoria: se pierde el récord al cerrar, pero el juego sigue funcionando.
 */
export function getSafeStorage(): StorageLike | null {
  try {
    const probe = '__menterush__'
    window.localStorage.setItem(probe, probe)
    window.localStorage.removeItem(probe)
    return window.localStorage
  } catch {
    return null
  }
}
