import { useEffect, useRef } from 'react'

/** Un frame lento no debe robar tiempo de juego: se descarta lo que exceda. */
const MAX_DELTA_MS = 100

/**
 * Bucle de reloj sobre `requestAnimationFrame`. Es el único punto de la app que
 * mide tiempo real; se lo entrega al dominio como deltas.
 *
 * El callback se guarda en una ref para que cambiar de manejador no reinicie el
 * bucle a mitad de una ronda.
 */
export function useCountdown(active: boolean, onTick: (deltaMs: number) => void): void {
  const callbackRef = useRef(onTick)
  callbackRef.current = onTick

  useEffect(() => {
    if (!active) return

    let frame = 0
    let last = performance.now()

    const step = (now: number) => {
      // Volver de una pestaña en segundo plano produce saltos de segundos:
      // acotarlos evita perder una ronda por algo ajeno al jugador.
      const delta = Math.min(now - last, MAX_DELTA_MS)
      last = now
      if (delta > 0) callbackRef.current(delta)
      frame = requestAnimationFrame(step)
    }

    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [active])
}
