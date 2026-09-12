/**
 * Filtro del listado del blog por categoría y por etiqueta.
 *
 * Misma decisión que en ProjectFilter: los posts ya viajan embebidos en el
 * HTML desde el build, así que filtrar no cuesta ninguna petición. La API
 * acepta `?category=` y `?tag=`, pero usarlos aquí sería pedirle al servidor
 * que recorte una lista que el navegador ya tiene entera.
 *
 * El filtro es **uno solo**, no dos independientes. Categoría y etiqueta
 * combinadas producen intersecciones vacías con facilidad — elegir
 * «Infraestructura» + «nginx» cuando ningún post tiene ambas deja la página
 * en blanco sin que se entienda por qué. Con un único filtro activo, cada
 * clic siempre lleva a algún sitio.
 */

import { useMemo, useState } from 'react';
import type { Category, PostSummary, Tag } from '../../lib/types';
import type { Dictionary } from '../../lib/i18n';
import { formatDate } from '../../lib/i18n';
import type { Language } from '../../lib/types';

type Filter = { kind: 'category' | 'tag'; slug: string } | null;

interface Props {
  lang: Language;
  posts: PostSummary[];
  categories: Category[];
  tags: Tag[];
  dict: Dictionary;
  blogBasePath: string;
}

function matches(post: PostSummary, filter: Filter): boolean {
  if (filter === null) return true;
  if (filter.kind === 'category') return post.category.slug === filter.slug;
  return post.tags.some((tag) => tag.slug === filter.slug);
}

export default function BlogFilter({ lang, posts, categories, tags, dict, blogBasePath }: Props) {
  const [filter, setFilter] = useState<Filter>(null);

  const visible = useMemo(() => posts.filter((post) => matches(post, filter)), [posts, filter]);

  const isActive = (kind: 'category' | 'tag', slug: string) =>
    filter?.kind === kind && filter.slug === slug;

  /** Alterna: volver a pulsar el filtro activo lo quita. */
  const toggle = (kind: 'category' | 'tag', slug: string) =>
    setFilter(isActive(kind, slug) ? null : { kind, slug });

  return (
    <div>
      <div className="filters" role="group" aria-label={dict.blog.filterByCategory}>
        <button
          type="button"
          className={`chip ${filter === null ? 'is-active' : ''}`}
          onClick={() => setFilter(null)}
          aria-pressed={filter === null}
        >
          {dict.blog.filterAll}
          <span className="count">{posts.length}</span>
        </button>

        {categories.map((category) => {
          const count = posts.filter((post) => post.category.slug === category.slug).length;
          if (count === 0) return null;
          return (
            <button
              key={category.slug}
              type="button"
              className={`chip ${isActive('category', category.slug) ? 'is-active' : ''}`}
              onClick={() => toggle('category', category.slug)}
              aria-pressed={isActive('category', category.slug)}
            >
              <span className="dot" aria-hidden="true" />
              {category.name}
              <span className="count">{count}</span>
            </button>
          );
        })}
      </div>

      {tags.length > 0 && (
        <div className="filters filters-tags" role="group" aria-label={dict.blog.filterByTag}>
          {tags.map((tag) => {
            const count = posts.filter((post) =>
              post.tags.some((candidate) => candidate.slug === tag.slug),
            ).length;
            if (count === 0) return null;
            return (
              <button
                key={tag.slug}
                type="button"
                className={`chip chip-tag ${isActive('tag', tag.slug) ? 'is-active' : ''}`}
                onClick={() => toggle('tag', tag.slug)}
                aria-pressed={isActive('tag', tag.slug)}
              >
                #{tag.name}
                <span className="count">{count}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Sin esto, para quien navega con lector de pantalla el filtro no
          produce ningún efecto perceptible. */}
      <p className="sr-only" aria-live="polite">
        {visible.length} {dict.blog.title}
      </p>

      {visible.length === 0 ? (
        <p className="empty">{dict.blog.emptyFiltered}</p>
      ) : (
        <ul className="post-cards">
          {visible.map((post) => (
            <li key={post.slug}>
              <a href={`${blogBasePath}/${post.slug}`}>
                <p className="post-category">{post.category.name}</p>
                <h2>{post.title}</h2>
                <p className="post-excerpt">{post.excerpt}</p>
                {post.tags.length > 0 && (
                  <ul className="post-tags">
                    {post.tags.map((tag) => (
                      <li key={tag.slug}>#{tag.name}</li>
                    ))}
                  </ul>
                )}
                <p className="post-meta">
                  {formatDate(post.published_at, lang)} · {post.reading_minutes}{' '}
                  {dict.blog.readingTime}
                </p>
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
