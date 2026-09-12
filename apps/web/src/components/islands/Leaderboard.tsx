/**
 * Ranking de un juego.
 *
 * Isla separada del juego a propósito: se refresca cuando termina una
 * partida, pero también se puede consultar sin jugar. Mantenerla aparte evita
 * que el estado del ranking provoque re-renders del canvas.
 */

import { useEffect, useState } from 'react';
import { fetchLeaderboard } from '../../lib/api';
import type { Dictionary } from '../../lib/i18n';
import type { Score } from '../../lib/types';

interface Props {
  slug: string;
  dict: Dictionary;
}

export default function Leaderboard({ slug, dict }: Props) {
  const [scores, setScores] = useState<Score[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const { data, error } = await fetchLeaderboard(slug, 10);
      if (cancelled) return;
      if (error || !data) {
        setFailed(true);
        return;
      }
      setScores(data);
    }

    void load();
    // Se recarga cuando un juego avisa de que se guardó una puntuación.
    const onScoreSaved = (event: Event) => {
      if ((event as CustomEvent<{ slug: string }>).detail?.slug === slug) void load();
    };
    window.addEventListener('score:saved', onScoreSaved);

    return () => {
      cancelled = true;
      window.removeEventListener('score:saved', onScoreSaved);
    };
  }, [slug]);

  if (failed) return null; // un ranking caído no debe romper el juego

  return (
    <aside className="leaderboard">
      <h3>{dict.games.leaderboard}</h3>
      {scores === null ? (
        <p className="leaderboard-empty">{dict.common.loading}</p>
      ) : scores.length === 0 ? (
        <p className="leaderboard-empty">{dict.games.noScores}</p>
      ) : (
        <ol>
          {scores.map((entry, index) => (
            <li key={`${entry.nickname}-${entry.created_at}`}>
              <span className="rank">{index + 1}</span>
              {/* React escapa el texto por defecto; el apodo además se saneó
                  en el servidor. Dos capas para el mismo dato de entrada. */}
              <span className="who">{entry.nickname}</span>
              <span className="points">{entry.score}</span>
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}
