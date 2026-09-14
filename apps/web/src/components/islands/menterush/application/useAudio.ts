import { useEffect, useMemo, useRef } from 'react'

/**
 * Motor de sonido sintetizado con Web Audio API.
 *
 * No hay archivos de audio: cero peso de descarga y, sobre todo, el tono puede
 * calcularse en runtime para que suba con el combo — algo imposible con samples
 * fijos. Si el navegador no soporta Web Audio, todo queda en no-op.
 */
export interface AudioEngine {
  /** Debe llamarse dentro de un gesto del usuario para desbloquear el audio. */
  unlock(): void
  /** Aparición de un número; el pitch sube dentro de la secuencia. */
  note(index: number, total: number): void
  correct(tier: number): void
  wrong(): void
  countdown(step: number): void
  record(): void
  gameOver(): void
}

const BASE_FREQ = 220

function semitone(base: number, steps: number): number {
  return base * Math.pow(2, steps / 12)
}

type WindowWithAudio = Window & { webkitAudioContext?: typeof AudioContext }

function createContext(): AudioContext | null {
  if (typeof window === 'undefined') return null
  const Ctor = window.AudioContext ?? (window as WindowWithAudio).webkitAudioContext
  if (!Ctor) return null
  try {
    return new Ctor()
  } catch {
    return null
  }
}

export function useAudio(enabled: boolean): AudioEngine {
  const contextRef = useRef<AudioContext | null>(null)
  const enabledRef = useRef(enabled)
  enabledRef.current = enabled

  useEffect(() => {
    return () => {
      void contextRef.current?.close()
      contextRef.current = null
    }
  }, [])

  return useMemo<AudioEngine>(() => {
    const ensure = (): AudioContext | null => {
      if (!enabledRef.current) return null
      contextRef.current ??= createContext()
      const ctx = contextRef.current
      // Los navegadores arrancan el contexto suspendido hasta el primer gesto.
      if (ctx?.state === 'suspended') void ctx.resume()
      return ctx
    }

    /** Una nota corta con envolvente propia: ataque rápido y caída suave. */
    const tone = (
      freq: number,
      durationMs: number,
      type: OscillatorType = 'triangle',
      gain = 0.18,
      startOffsetMs = 0,
    ): void => {
      const ctx = ensure()
      if (!ctx) return

      const start = ctx.currentTime + startOffsetMs / 1000
      const end = start + durationMs / 1000

      const osc = ctx.createOscillator()
      const envelope = ctx.createGain()
      osc.type = type
      osc.frequency.setValueAtTime(freq, start)

      envelope.gain.setValueAtTime(0, start)
      envelope.gain.linearRampToValueAtTime(gain, start + 0.012)
      envelope.gain.exponentialRampToValueAtTime(0.0001, end)

      osc.connect(envelope).connect(ctx.destination)
      osc.start(start)
      osc.stop(end + 0.02)
    }

    return {
      unlock() {
        ensure()
      },

      note(index, total) {
        // El pitch asciende a lo largo de la secuencia: tensión que se acumula.
        const progress = total > 1 ? index / (total - 1) : 0
        tone(semitone(BASE_FREQ, 5 + progress * 7), 110, 'triangle', 0.12)
      },

      correct(tier) {
        // Arpegio ascendente; sube un semitono por tier de combo.
        const base = semitone(BASE_FREQ * 2, tier)
        tone(base, 90, 'triangle', 0.16)
        tone(semitone(base, 4), 90, 'triangle', 0.14, 70)
        tone(semitone(base, 7), 160, 'triangle', 0.14, 140)
      },

      wrong() {
        tone(semitone(BASE_FREQ, -5), 260, 'sawtooth', 0.14)
        tone(semitone(BASE_FREQ, -12), 420, 'sawtooth', 0.12, 90)
      },

      countdown(step) {
        tone(semitone(BASE_FREQ * 2, step * 2), 120, 'square', 0.1)
      },

      record() {
        const base = BASE_FREQ * 3
        ;[0, 4, 7, 12].forEach((s, i) => tone(semitone(base, s), 200, 'triangle', 0.15, i * 90))
      },

      gameOver() {
        ;[0, -3, -7, -12].forEach((s, i) =>
          tone(semitone(BASE_FREQ, s), 320, 'sawtooth', 0.13, i * 150),
        )
      },
    }
  }, [])
}
