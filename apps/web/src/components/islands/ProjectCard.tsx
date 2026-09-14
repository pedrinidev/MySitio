/**
 * La tarjeta de un proyecto.
 *
 * Vive aparte porque la usan dos sitios con comportamientos distintos: el
 * carril del inicio, que se desplaza solo, y la rejilla quieta de la página
 * de Proyectos. Tenerla en un único lugar evita que se separen con el
 * tiempo — que es exactamente lo que pasó con los dos PNG del logotipo.
 *
 * Las clases son globales (islands.css) a propósito: así también las puede
 * reutilizar un componente de Astro sin arrastrar React.
 */

import type { CSSProperties } from 'react';
import type { ProjectSummary } from '../../lib/types';

interface Props {
  project: ProjectSummary;
  basePath: string;
  /** Copia del carril infinito: no se anuncia ni se tabula. */
  clone?: boolean;
}

export default function ProjectCard({ project, basePath, clone = false }: Props) {
  return (
    <li className="card" aria-hidden={clone}>
      <a
        href={`${basePath}/${project.slug}`}
        className="card-link"
        tabIndex={clone ? -1 : undefined}
      >
        {project.cover_url ? (
          <img
            src={project.cover_url}
            alt=""
            className="cover"
            loading="lazy"
            width={640}
            height={400}
          />
        ) : (
          <div className="cover cover-placeholder" aria-hidden="true">
            <span>{project.title.slice(0, 2).toUpperCase()}</span>
          </div>
        )}

        <div className="card-body">
          <div className="card-meta">
            <span className="year">{project.year}</span>
            {project.featured && (
              <span className="star" aria-hidden="true">
                ★
              </span>
            )}
          </div>
          <h3 className="card-title">{project.title}</h3>
          <p className="card-tagline">{project.tagline}</p>
          <ul className="tech-list">
            {project.technologies.slice(0, 4).map((tech) => (
              <li key={tech.slug} style={{ '--chip-color': tech.color } as CSSProperties}>
                <span className="dot" aria-hidden="true" />
                {tech.name}
              </li>
            ))}
          </ul>
        </div>
      </a>
    </li>
  );
}
