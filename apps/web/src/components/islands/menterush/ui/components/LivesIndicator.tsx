import { useEffect, useRef, useState } from 'react'
import styles from './components.module.css'

/** Las vidas restantes; la que se pierde se rompe con una animación. */
export function LivesIndicator({ lives, total }: { lives: number; total: number }) {
  const [breakingIndex, setBreakingIndex] = useState(-1)
  const previousRef = useRef(lives)

  useEffect(() => {
    if (lives < previousRef.current) {
      setBreakingIndex(lives)
      const id = setTimeout(() => setBreakingIndex(-1), 500)
      previousRef.current = lives
      return () => clearTimeout(id)
    }
    previousRef.current = lives
    return undefined
  }, [lives])

  return (
    <div className={styles.lives} aria-label={`${lives} de ${total} vidas`}>
      {Array.from({ length: total }, (_, index) => {
        const lost = index >= lives
        return (
          <span
            key={index}
            className={[
              styles.life,
              lost ? styles.lost : '',
              index === breakingIndex ? styles.breaking : '',
            ]
              .filter(Boolean)
              .join(' ')}
            aria-hidden="true"
          >
            {/* Corazón lleno mientras queda, hueco cuando se pierde. */}
            {lost ? '♡' : '♥'}
          </span>
        )
      })}
    </div>
  )
}
