import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Tope de la respuesta: 12 números de una cifra dan 108, y 8 de dos cifras dan
 * 792. En ningún caso hacen falta más de tres dígitos, ni el signo menos.
 */
const MAX_DIGITS = 3

export interface Keypad {
  /** Lo tecleado hasta ahora. */
  readonly raw: string
  /** Valor numérico, o `null` si aún no hay nada que enviar. */
  readonly value: number | null
  append(digit: string): void
  backspace(): void
  clear(): void
  confirm(): void
}

/**
 * Entrada unificada: teclado físico en escritorio y teclado propio en móvil
 * comparten el mismo estado, así nunca se desincronizan.
 *
 * En móvil no se usa el teclado nativo a propósito: tarda en abrirse, tapa media
 * pantalla y rompe el ritmo del juego.
 *
 * No hay tecla de signo porque el generador garantiza que el total nunca es
 * negativo (ver `numberGenerator.ts`).
 */
export function useKeypad(params: {
  active: boolean
  onSubmit: (value: number) => void
  /**
   * Si lo tecleado coincide con este valor, la respuesta se envía sola. Es la
   * respuesta correcta de la ronda: acertar no debe costar una pulsación extra,
   * que además consume tiempo del reloj. Fallar sí exige confirmar.
   */
  autoSubmitValue: number | null
}): Keypad {
  const { active, onSubmit, autoSubmitValue } = params

  const [digits, setDigits] = useState('')

  const submitRef = useRef(onSubmit)
  submitRef.current = onSubmit

  // Cada nueva ronda empieza con el marcador limpio.
  useEffect(() => {
    if (!active) setDigits('')
  }, [active])

  const value = digits === '' ? null : Number(digits)
  const valueRef = useRef(value)
  valueRef.current = value

  const append = useCallback((digit: string) => {
    if (!/^[0-9]$/.test(digit)) return
    setDigits((current) => (current.length >= MAX_DIGITS ? current : current + digit))
  }, [])

  const backspace = useCallback(() => {
    setDigits((current) => current.slice(0, -1))
  }, [])

  const clear = useCallback(() => setDigits(''), [])

  const confirm = useCallback(() => {
    const current = valueRef.current
    if (current === null) return
    submitRef.current(current)
  }, [])

  // Acierto reconocido al vuelo, sin pulsar "responder".
  useEffect(() => {
    if (!active || value === null || autoSubmitValue === null) return
    if (value === autoSubmitValue) submitRef.current(value)
  }, [active, value, autoSubmitValue])

  // Teclado físico: jugar en escritorio no debe requerir el ratón.
  useEffect(() => {
    if (!active) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return

      if (/^[0-9]$/.test(event.key)) {
        event.preventDefault()
        append(event.key)
        return
      }

      switch (event.key) {
        case 'Backspace':
          event.preventDefault()
          backspace()
          break
        case 'Enter':
          event.preventDefault()
          confirm()
          break
        case 'Escape':
          event.preventDefault()
          clear()
          break
        default:
          break
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [active, append, backspace, confirm, clear])

  return { raw: digits, value, append, backspace, clear, confirm }
}
