import type { DigitMode, OperationMode, PlayMode, SchoolLevel } from '../domain'
import { STORAGE_KEYS, type StorageLike } from './storageKeys'

/**
 * Preferencia de tema. `auto` sigue al sistema operativo; es el valor de partida
 * hasta que el jugador elige uno a mano.
 */
export type ThemePreference = 'auto' | 'light' | 'dark'

/** Preferencias del jugador. Equivale a `SharedPreferences("operacion")`. */
export interface Settings {
  readonly mode: OperationMode
  readonly digits: DigitMode
  readonly play: PlayMode
  readonly level: SchoolLevel
  readonly sound: boolean
  readonly haptics: boolean
  readonly theme: ThemePreference
}

export const DEFAULT_SETTINGS: Settings = {
  mode: 'SUMA',
  digits: 'ONE',
  play: 'RETO',
  level: 'MEDIO',
  sound: true,
  haptics: true,
  theme: 'auto',
}

export interface SettingsRepository {
  load(): Settings
  save(settings: Settings): void
}

function readBoolean(value: unknown, fallback: boolean): boolean {
  return typeof value === 'boolean' ? value : fallback
}

function parseSettings(raw: string | null): Settings {
  if (!raw) return DEFAULT_SETTINGS
  try {
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null) return DEFAULT_SETTINGS
    const data = parsed as Record<string, unknown>
    return {
      // Cualquier valor que no sea exactamente 'MIXTO' cae en 'SUMA', igual que
      // `OperationMode.fromPreference()` en MentePro.
      mode: data['mode'] === 'MIXTO' ? 'MIXTO' : 'SUMA',
      digits: data['digits'] === 'TWO' ? 'TWO' : 'ONE',
      play: data['play'] === 'PRACTICA' ? 'PRACTICA' : 'RETO',
      level:
        data['level'] === 'INICIAL' || data['level'] === 'AVANZADO' ? data['level'] : 'MEDIO',
      sound: readBoolean(data['sound'], DEFAULT_SETTINGS.sound),
      haptics: readBoolean(data['haptics'], DEFAULT_SETTINGS.haptics),
      // Cualquier valor desconocido vuelve a seguir al sistema.
      theme: data['theme'] === 'light' || data['theme'] === 'dark' ? data['theme'] : 'auto',
    }
  } catch {
    return DEFAULT_SETTINGS
  }
}

export function createSettingsRepository(storage: StorageLike | null): SettingsRepository {
  let memory: Settings = DEFAULT_SETTINGS

  return {
    load(): Settings {
      if (!storage) return memory
      try {
        return parseSettings(storage.getItem(STORAGE_KEYS.settings))
      } catch {
        return DEFAULT_SETTINGS
      }
    },

    save(settings: Settings): void {
      memory = settings
      if (!storage) return
      try {
        storage.setItem(STORAGE_KEYS.settings, JSON.stringify(settings))
      } catch {
        // Sin almacenamiento persistente seguimos con el valor en memoria.
      }
    },
  }
}
