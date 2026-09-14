/**
 * Filtro de proyectos por tecnología, en rejilla quieta.
 *
 * Los datos llegan ya embebidos en el HTML desde el build: filtrar NO hace
 * ninguna petición. Con tres o treinta proyectos, pedirle al servidor que
 * recorte una lista que el navegador ya tiene entera sería añadir latencia
 * a cambio de nada.
 *
 * Aquí las tarjetas NO se mueven, y es deliberado. A esta página se entra a
 * comparar proyectos con calma: un carril que avanza solo obliga a
 * perseguir lo que se está leyendo. El movimiento se llevó al inicio, donde
 * la portada sí gana con él (ver ProjectRail).
 *
 * Y una rejilla enseña todo de una vez: con un carril había que desplazarse
 * para descubrir que existían más proyectos.
 */

import { useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import type { ProjectSummary, Technology } from '../../lib/types';
import ProjectCard from './ProjectCard';
import type { Dictionary } from '../../lib/i18n';

interface Props {
  projects: ProjectSummary[];
  technologies: Technology[];
  dict: Dictionary;
  projectBasePath: string;
}

export default function ProjectFilter({ projects, technologies, dict, projectBasePath }: Props) {
  const [active, setActive] = useState<string | null>(null);

  const visible = useMemo(
    () =>
      active ? projects.filter((p) => p.technologies.some((t) => t.slug === active)) : projects,
    [projects, active],
  );

  return (
    <div>
      <div className="filters" role="group" aria-label={dict.projects.filterBy}>
        <button
          type="button"
          className={`chip ${active === null ? 'is-active' : ''}`}
          onClick={() => setActive(null)}
          aria-pressed={active === null}
        >
          {dict.projects.filterAll}
          <span className="count">{projects.length}</span>
        </button>

        {technologies.map((tech) => {
          const count = projects.filter((p) =>
            p.technologies.some((t) => t.slug === tech.slug),
          ).length;
          if (count === 0) return null;
          return (
            <button
              key={tech.slug}
              type="button"
              className={`chip ${active === tech.slug ? 'is-active' : ''}`}
              onClick={() => setActive(active === tech.slug ? null : tech.slug)}
              aria-pressed={active === tech.slug}
              style={{ '--chip-color': tech.color } as CSSProperties}
            >
              <span className="dot" aria-hidden="true" />
              {tech.name}
              <span className="count">{count}</span>
            </button>
          );
        })}
      </div>

      {/* aria-live avisa a los lectores de pantalla de que la lista cambió;
          sin esto, para alguien que navega por voz el filtro no hace nada. */}
      <p className="sr-only" aria-live="polite">
        {visible.length} {dict.projects.title}
      </p>

      {visible.length === 0 ? (
        <p className="empty">{dict.projects.empty}</p>
      ) : (
        <ul className="cards-grid">
          {visible.map((project) => (
            <ProjectCard key={project.slug} project={project} basePath={projectBasePath} />
          ))}
        </ul>
      )}
    </div>
  );
}
