import styles from './effects.module.css'

/**
 * Destello de pantalla completa. Se monta con una `key` distinta en cada evento
 * para que la animación vuelva a arrancar.
 */
export function ScreenFlash({ variant }: { variant: 'correct' | 'wrong' }) {
  return (
    <div
      className={`${styles.flash} ${variant === 'correct' ? styles.flashCorrect : styles.flashWrong}`}
      aria-hidden="true"
    />
  )
}

/** Viñeta latiendo, reservada a los tiers altos de combo. */
export function ComboVignette() {
  return <div className={styles.vignette} aria-hidden="true" />
}
