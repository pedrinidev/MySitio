import { useEffect, useState } from 'react'
import styles from './components.module.css'

/**
 * Racha actual y, en modo Reto, el multiplicador que aplica.
 *
 * No hay estrellas ni número de escalón: el multiplicador ya dice algo concreto
 * —cuánto vale cada acierto— y cualquier otro indicador sería el mismo dato
 * repetido.
 *
 * Se muestra también en Práctica: la racha ya se rompe al fallar y ya está a la
 * vista, así que el multiplicador no añade castigo, solo hace visible lo que se
 * está ganando. Es la parte emocionante de encadenar aciertos.
 */
export function ComboMeter({ combo, multiplier }: { combo: number; multiplier: number }) {
  const [bump, setBump] = useState(false)

  useEffect(() => {
    if (combo === 0) return
    setBump(true)
    const id = setTimeout(() => setBump(false), 320)
    return () => clearTimeout(id)
  }, [combo])

  if (combo === 0) {
    return (
      <div className={styles.combo}>
        <span className={styles.comboLabel}>Sin racha</span>
      </div>
    )
  }

  return (
    <div className={`${styles.combo} ${bump ? styles.comboBump : ''}`}>
      <span className={`${styles.comboValue} tabular`}>{combo}</span>
      <span className={styles.comboLabel}>seguidos</span>
      <span className={styles.multiplier}>×{multiplier}</span>
    </div>
  )
}
