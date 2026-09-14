import type { PointerEvent as ReactPointerEvent, MouseEvent as ReactMouseEvent } from 'react'
import type { Keypad as KeypadState } from '../../application'
import styles from './components.module.css'

const DIGITS = ['1', '2', '3', '4', '5', '6', '7', '8', '9'] as const

/**
 * Dispara la acción en cuanto el dedo toca, no al levantarlo.
 *
 * Con `onClick` el navegador espera al `pointerup`: en un juego contrarreloj esa
 * espera se nota, y si el dedo se desliza fuera de la tecla la pulsación se
 * pierde. `preventDefault` evita además el click sintético posterior, el foco y
 * el zoom por doble toque.
 *
 * El `onClick` se conserva solo para activaciones por teclado (Enter o Espacio
 * sobre el botón), que llegan con `detail === 0` y no generan eventos de puntero.
 */
function alPulsar(accion: () => void) {
  return {
    onPointerDown: (event: ReactPointerEvent<HTMLButtonElement>) => {
      event.preventDefault()
      accion()
    },
    onClick: (event: ReactMouseEvent<HTMLButtonElement>) => {
      if (event.detail === 0) accion()
    },
  }
}

/**
 * Teclado numérico propio. En móvil sustituye al del sistema (que tarda en
 * abrirse y tapa la pantalla); en escritorio duplica el teclado físico para que
 * las teclas disponibles estén siempre a la vista.
 *
 * No hay tecla de signo: el total nunca es negativo. La tecla de confirmar solo
 * hace falta para enviar una respuesta equivocada — al acertar se envía sola.
 */
export function Keypad({ keypad }: { keypad: KeypadState }) {
  return (
    <div className={styles.keypad}>
      {DIGITS.map((digit) => (
        <button key={digit} className={styles.key} {...alPulsar(() => keypad.append(digit))}>
          {digit}
        </button>
      ))}

      <button
        className={`${styles.key} ${styles.muted}`}
        aria-label="Borrar"
        {...alPulsar(keypad.backspace)}
      >
        ⌫
      </button>

      <button className={styles.key} {...alPulsar(() => keypad.append('0'))}>
        0
      </button>

      <button
        className={`${styles.key} ${styles.accent}`}
        disabled={keypad.value === null}
        aria-label="Responder"
        {...alPulsar(keypad.confirm)}
      >
        ✓
      </button>
    </div>
  )
}
