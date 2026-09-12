/**
 * Búsqueda en el blog.
 *
 * Esta isla SÍ consulta la API, porque busca en el cuerpo completo de los
 * posts y ese texto no está embebido en la página de listado.
 *
 * Dos cuidados: un *debounce* de 300 ms para no disparar una consulta por
 * tecla, y un contador de petición para descartar respuestas que llegan
 * fuera de orden. Sin lo segundo, escribir «docker» rápido puede acabar
 * mostrando los resultados de «doc» si esa respuesta llega la última.
 */

import { useEffect, useRef, useState } from 'react';
import { searchPosts } from '../../lib/api';
import type { Language, PostSummary } from '../../lib/types';
import type { Dictionary } from '../../lib/i18n';

interface Props {
  lang: Language;
  dict: Dictionary;
  blogBasePath: string;
}

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 2;

export default function BlogSearch({ lang, dict, blogBasePath }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<PostSummary[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < MIN_QUERY_LENGTH) {
      setResults(null);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    const currentRequest = ++requestId.current;

    const timer = setTimeout(async () => {
      const { data, error: fetchError } = await searchPosts(trimmed, lang);

      // Respuesta obsoleta: el usuario ya siguió escribiendo. Se descarta.
      if (currentRequest !== requestId.current) return;

      setLoading(false);
      if (fetchError) {
        setError(fetchError);
        setResults(null);
      } else {
        setError(null);
        setResults(data?.results ?? []);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [query, lang]);

  return (
    <div className="search">
      <label className="sr-only" htmlFor="blog-search">
        {dict.blog.search}
      </label>
      <div className="search-field">
        <svg viewBox="0 0 20 20" className="search-icon" aria-hidden="true">
          <path
            d="M9 3a6 6 0 104.47 10.03l3.25 3.25a.75.75 0 101.06-1.06l-3.25-3.25A6 6 0 009 3zm0 1.5a4.5 4.5 0 110 9 4.5 4.5 0 010-9z"
            fill="currentColor"
          />
        </svg>
        <input
          id="blog-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={dict.blog.searchPlaceholder}
          autoComplete="off"
        />
        {loading && <span className="spinner" aria-hidden="true" />}
      </div>

      <div aria-live="polite">
        {error && <p className="search-error">{dict.common.error}</p>}

        {results !== null && !error && (
          <>
            <p className="search-count">
              {results.length} {dict.blog.resultsFor} «{query.trim()}»
            </p>
            {results.length === 0 ? (
              <p className="empty">
                {dict.blog.noResults} «{query.trim()}»
              </p>
            ) : (
              <ul className="search-results">
                {results.map((post) => (
                  <li key={post.slug}>
                    <a href={`${blogBasePath}/${post.slug}`}>
                      <span className="result-category">{post.category.name}</span>
                      <span className="result-title">{post.title}</span>
                      <span className="result-excerpt">{post.excerpt}</span>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </div>
  );
}
