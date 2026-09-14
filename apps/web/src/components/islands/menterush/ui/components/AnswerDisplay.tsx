import styles from './components.module.css'

/** Lo que el jugador lleva tecleado, con cursor cuando aún está vacío. */
export function AnswerDisplay({ raw }: { raw: string }) {
  const empty = raw === '' || raw === '-'

  return (
    <div className={`${styles.answerDisplay} tabular`} aria-live="polite">
      {empty ? (
        <>
          <span className={styles.answerPlaceholder}>{raw === '-' ? '-' : '?'}</span>
          <span className={styles.caret} />
        </>
      ) : (
        raw
      )}
    </div>
  )
}
