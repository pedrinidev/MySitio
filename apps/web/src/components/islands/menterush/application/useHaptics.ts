import { useMemo, useRef } from 'react'

/** Vibración en móvil. No-op donde no exista la API o esté desactivada. */
export interface Haptics {
  light(): void
  success(): void
  error(): void
  gameOver(): void
}

export function useHaptics(enabled: boolean): Haptics {
  const enabledRef = useRef(enabled)
  enabledRef.current = enabled

  return useMemo<Haptics>(() => {
    const vibrate = (pattern: number | number[]): void => {
      if (!enabledRef.current) return
      if (typeof navigator === 'undefined' || typeof navigator.vibrate !== 'function') return
      try {
        navigator.vibrate(pattern)
      } catch {
        // Algunos navegadores lanzan si la pestaña no está activa.
      }
    }

    return {
      light: () => vibrate(8),
      success: () => vibrate(18),
      error: () => vibrate([40, 60, 90]),
      gameOver: () => vibrate([70, 80, 70, 80, 160]),
    }
  }, [])
}
