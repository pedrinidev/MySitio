/**
 * MenteRush, jugable dentro del portafolio.
 *
 * El código del juego vive en `./menterush/` y viene del repositorio
 * https://github.com/pedrinidev/MenteRush. Se copió tal cual —dominio,
 * hooks, datos y componentes— y solo tiene tres adaptaciones, todas
 * anotadas en su sitio:
 *
 *  1. `application/useTheme.ts` ya no escribe `data-theme` en el documento.
 *     Escribía ahí porque era dueño de la página; aquí habría cambiado el
 *     tema del sitio entero y borrado la elección del visitante.
 *  2. `styles/tokens.css` y `styles/tiers.css` cuelgan de `.menterush-root`
 *     en vez de `:root`. Sus reglas globales —`body{overflow:hidden}`,
 *     `button{border:none}`— habrían dejado el sitio sin scroll y sin
 *     botones estilados.
 *  3. `App.tsx` avisa de cuándo empieza y termina una partida, para poder
 *     engancharla al ranking del sitio. El juego no sabe que el ranking
 *     existe: solo dice «empecé» y «terminé con tanto».
 *
 * Ninguna función se perdió: combos, sonido, vibración, teclado, partículas,
 * récords propios y su interruptor de tema siguen igual.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { App } from './menterush/App';
import { startGameSession, submitScore } from '../../lib/api';
import type { Dictionary } from '../../lib/i18n';
import './menterush/styles/tokens.css';
import './menterush/styles/tiers.css';

interface Props {
  slug: string;
  dict: Dictionary;
}

type Phase = 'idle' | 'over' | 'saving' | 'saved';

interface Resumen {
  score: number;
  bestCombo: number;
  rounds: number;
  correct: number;
  total: number;
}

/** Lienzo de diseño del juego, en píxeles lógicos. Es la disposición
 *  vertical con la que MenteRush se diseñó y se probó. */
const DISENO_ANCHO = 430;
const DISENO_ALTO = 780;

export default function MenteRush({ slug, dict }: Props) {
  const [phase, setPhase] = useState<Phase>('idle');
  const [score, setScore] = useState(0);
  const [nickname, setNickname] = useState('');
  const [rank, setRank] = useState<number | null>(null);

  const token = useRef<string | null>(null);
  const startedAt = useRef(0);

  // Escalado a medida, y no a base de ajustar CSS.
  //
  // El juego se dibuja siempre en un lienzo de DISEÑO fijo y después se
  // reduce o agranda entero hasta llenar el marco. Es la única forma de
  // garantizar que se ve completo en cualquier pantalla sin barras de
  // desplazamiento: perseguir uno a uno los huecos y márgenes en píxeles
  // del juego funcionaba en un tamaño y fallaba en el siguiente.
  //
  // Además el juego ve siempre el mismo ancho, así que usa la disposición
  // vertical para la que fue diseñado y probado, en vez de una intermedia
  // que nadie miró nunca.
  const marco = useRef<HTMLDivElement>(null);
  const [escala, setEscala] = useState(1);

  useEffect(() => {
    const el = marco.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const medir = () => {
      const { width, height } = el.getBoundingClientRect();
      if (!width || !height) return;
      setEscala(Math.min(width / DISENO_ANCHO, height / DISENO_ALTO));
    };
    medir();
    const observador = new ResizeObserver(medir);
    observador.observe(el);
    return () => observador.disconnect();
  }, []);

  // El token se pide al empezar, igual que en Snake: el servidor solo acepta
  // una puntuación por sesión y comprueba que la partida haya durado algo
  // plausible. Sin esto, mandar un récord sería una petición de una línea.
  const onRunStart = useCallback(async () => {
    setPhase('idle');
    setRank(null);
    startedAt.current = Date.now();
    const { data } = await startGameSession(slug);
    token.current = data?.token ?? null;
  }, [slug]);

  // El resumen entero, no solo la puntuación: la mejor racha y las rondas
  // superadas viajan con ella y quedan guardadas junto al récord. Así la
  // tabla no es solo «cuántos puntos» sino cómo se consiguieron.
  const [resumen, setResumen] = useState<Resumen | null>(null);

  const onRunEnd = useCallback((datos: Resumen) => {
    setResumen(datos);
    setScore(datos.score);
    setPhase('over');
  }, []);

  async function save() {
    if (!token.current) return;
    setPhase('saving');
    const { data } = await submitScore(slug, {
      token: token.current,
      nickname,
      score,
      duration_ms: Date.now() - startedAt.current,
      stats: resumen
        ? {
            best_combo: resumen.bestCombo,
            rounds: resumen.rounds,
            correct: resumen.correct,
            total: resumen.total,
          }
        : {},
    });
    setRank(data?.rank ?? null);
    setPhase('saved');
    // El ranking es una isla aparte: se le avisa de que hay dato nuevo.
    window.dispatchEvent(new CustomEvent('score:saved', { detail: { slug } }));
    token.current = null;
  }

  return (
    <div>
      <div className="menterush-frame" ref={marco}>
        <div
          className="menterush-lienzo"
          style={{
            width: DISENO_ANCHO,
            height: DISENO_ALTO,
            transform: `translate(-50%, -50%) scale(${escala})`,
          }}
        >
          <App onRunStart={() => void onRunStart()} onRunEnd={onRunEnd} />
        </div>
      </div>

      {/* La tira de guardado vive FUERA del juego, no dentro de sus
          pantallas. Así el juego sigue siendo el del repositorio y esto es
          decoración del portafolio que se puede quitar sin tocarlo. */}
      {phase !== 'idle' && (
        <div className="menterush-save">
          <p className="menterush-save-score">
            {dict.games.score}: <strong>{score}</strong>
            {resumen && resumen.bestCombo > 0 && (
              <span className="menterush-racha"> · racha {resumen.bestCombo}</span>
            )}
            {rank !== null && (
              <span className="menterush-rank">
                {' · '}
                {dict.games.rank} {rank}
              </span>
            )}
          </p>

          {phase === 'saved' ? (
            <p className="menterush-saved">{dict.games.saved}</p>
          ) : (
            <>
              <input
                type="text"
                maxLength={16}
                value={nickname}
                onChange={(event) => setNickname(event.target.value)}
                placeholder={dict.games.yourName}
                className="overlay-input"
              />
              <button
                type="button"
                className="submit"
                disabled={phase === 'saving'}
                onClick={() => void save()}
              >
                {phase === 'saving' ? dict.games.saving : dict.games.submit}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
