import { useEffect, useRef } from 'react'
import { useGameEngine } from './application'
import { GameOverScreen } from './ui/screens/GameOverScreen'
import { GameScreen } from './ui/screens/GameScreen'
import { HomeScreen } from './ui/screens/HomeScreen'

export interface AppProps {
  /** Se llama al arrancar una partida de RETO. */
  onRunStart?: () => void
  /** Se llama al terminar una partida de RETO, con el resumen de la partida. */
  onRunEnd?: (resumen: {
    score: number
    bestCombo: number
    rounds: number
    correct: number
    total: number
  }) => void
}

/**
 * Raíz de la aplicación. Solo decide qué pantalla toca y expone el tier de
 * combo como `data-tier`, del que cuelga toda la paleta de acento.
 *
 * Añadido para vivir dentro del portafolio: la clase `menterush-root` y el
 * atributo `data-theme`. Toda la hoja de estilos del juego cuelga de esa
 * clase, así que su tema y sus reglas globales terminan aquí y no se
 * desbordan a la página que lo aloja. En el MenteRush original ese papel lo
 * hacía `:root`, porque el juego era la página entera.
 */
export function App({ onRunStart, onRunEnd }: AppProps = {}) {
  const engine = useGameEngine()
  const { status } = engine.state

  // Avisos al contenedor para el ranking del sitio. El juego no sabe que
  // existe: solo dice «empecé» y «terminé con tanto», y quien lo aloja
  // decide qué hacer. Añadido para el portafolio; el MenteRush original
  // guarda sus récords solo en el navegador y sigue haciéndolo.
  //
  // Únicamente el modo RETO puntúa. La práctica tiene número de rondas
  // fijo y vidas infinitas: meterla en la misma tabla mezclaría dos cosas
  // que no se pueden comparar.
  const anterior = useRef<string>(status)
  useEffect(() => {
    const previo = anterior.current
    anterior.current = status
    if (previo === status) return
    if (engine.state.play !== 'RETO') return
    if (previo === 'idle' && status !== 'idle') onRunStart?.()
    if (status === 'gameOver')
      onRunEnd?.({
        score: engine.state.score,
        bestCombo: engine.state.bestCombo,
        rounds: engine.state.roundsCleared,
        correct: engine.state.correctAnswers,
        total: engine.state.totalAnswers,
      })
  }, [status, engine.state, onRunStart, onRunEnd])

  return (
    <div
      className="menterush-root"
      data-tier={engine.tier}
      data-theme={engine.theme}
      style={{ height: '100%' }}
    >
      {status === 'idle' && <HomeScreen engine={engine} />}
      {status === 'gameOver' && <GameOverScreen engine={engine} />}
      {status !== 'idle' && status !== 'gameOver' && <GameScreen engine={engine} />}
    </div>
  )
}
