/**
 * Quiz DevOps.
 *
 * Las preguntas llegan prerenderizadas desde el build; las respuestas
 * correctas NUNCA. El navegador solo sabe qué opción eligió el jugador: la
 * corrección, la puntuación y la explicación vienen del servidor al enviar.
 *
 * Es lo que hace que el ranking signifique algo. Si la corrección fuera local,
 * cualquiera con el inspector abierto podría publicar la puntuación máxima.
 */

import { useState } from 'react';
import { startGameSession, submitScore } from '../../lib/api';
import type { ScoreSubmitResponse } from '../../lib/api';
import type { Dictionary } from '../../lib/i18n';
import type { Language, QuizQuestion } from '../../lib/types';

interface Props {
  slug: string;
  questions: QuizQuestion[];
  lang: Language;
  dict: Dictionary;
}

type Phase = 'intro' | 'playing' | 'submitting' | 'done' | 'error';

export default function QuizGame({ slug, questions, lang, dict }: Props) {
  const [phase, setPhase] = useState<Phase>('intro');
  const [token, setToken] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [nickname, setNickname] = useState('');
  const [result, setResult] = useState<ScoreSubmitResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const total = questions.length;
  const question = questions[index];

  async function start() {
    const { data, error } = await startGameSession(slug);
    if (error || !data) {
      setErrorMessage(error ?? dict.common.error);
      setPhase('error');
      return;
    }
    setToken(data.token);
    setIndex(0);
    setAnswers({});
    setResult(null);
    setPhase('playing');
  }

  function choose(optionId: number) {
    setAnswers((previous) => ({ ...previous, [question.id]: optionId }));
  }

  async function finish() {
    if (!token) return;
    setPhase('submitting');

    const payload = {
      token,
      nickname,
      answers: Object.entries(answers).map(([questionId, optionId]) => ({
        question: Number(questionId),
        option: optionId,
      })),
    };

    const { data, error } = await submitScore(slug, payload, lang);

    if (error || !data) {
      setErrorMessage(error ?? dict.common.error);
      setPhase('error');
      return;
    }
    setResult(data);
    setPhase('done');
    window.dispatchEvent(new CustomEvent('score:saved', { detail: { slug } }));
  }

  /* ── Pantallas ─────────────────────────────────────────────── */

  if (phase === 'intro') {
    return (
      <div className="game-panel">
        <p className="game-intro">
          {total} {dict.games.quiz.question.toLowerCase()}s · {dict.games.subtitle}
        </p>
        <label className="field">
          <span>{dict.games.yourName}</span>
          <input
            type="text"
            maxLength={16}
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
            placeholder="…"
          />
        </label>
        <button type="button" className="submit" onClick={() => void start()}>
          {dict.games.start}
        </button>
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <div className="game-panel" role="alert">
        <p className="form-error">{errorMessage}</p>
        <button type="button" className="submit" onClick={() => setPhase('intro')}>
          {dict.common.retry}
        </button>
      </div>
    );
  }

  if (phase === 'done' && result) {
    return (
      <div className="game-panel">
        <div className="quiz-result">
          <p className="result-score">{result.score}</p>
          <p className="result-detail">
            {result.correct} {dict.games.quiz.correctAnswers} {result.total} · {dict.games.rank} #
            {result.rank}
          </p>
        </div>

        <ol className="quiz-review">
          {result.details.map((entry) => {
            const reviewed = questions.find((q) => q.id === entry.question);
            if (!reviewed) return null;
            return (
              <li key={entry.question} className={entry.was_correct ? 'ok' : 'ko'}>
                <p className="review-question">{reviewed.text}</p>
                <p className="review-answer">
                  {entry.was_correct ? '✓ ' : '✗ '}
                  {reviewed.options.find((o) => o.id === entry.correct_option)?.text}
                </p>
                {entry.explanation && <p className="review-why">{entry.explanation}</p>}
              </li>
            );
          })}
        </ol>

        <button type="button" className="submit" onClick={() => setPhase('intro')}>
          {dict.games.playAgain}
        </button>
      </div>
    );
  }

  const selected = answers[question.id];
  const isLast = index === total - 1;

  return (
    <div className="game-panel">
      <div className="quiz-progress">
        <span>
          {dict.games.quiz.question} {index + 1} {dict.games.quiz.of} {total}
        </span>
        <div className="progress-track" role="presentation">
          <span style={{ width: `${((index + 1) / total) * 100}%` }} />
        </div>
      </div>

      <p className="quiz-question">{question.text}</p>

      <ul className="quiz-options">
        {question.options.map((option) => (
          <li key={option.id}>
            <button
              type="button"
              className={`quiz-option ${selected === option.id ? 'is-selected' : ''}`}
              onClick={() => choose(option.id)}
              aria-pressed={selected === option.id}
            >
              {option.text}
            </button>
          </li>
        ))}
      </ul>

      <button
        type="button"
        className="submit"
        disabled={selected === undefined || phase === 'submitting'}
        onClick={() => (isLast ? void finish() : setIndex(index + 1))}
      >
        {phase === 'submitting'
          ? dict.games.saving
          : isLast
            ? dict.games.quiz.finish
            : dict.games.quiz.next}
      </button>
    </div>
  );
}
