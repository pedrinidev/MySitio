/**
 * Filtro de proyectos por tecnología, en carril horizontal.
 *
 * Los datos llegan ya embebidos en el HTML desde el build: filtrar NO hace
 * ninguna petición. Con tres o treinta proyectos, pedirle al servidor que
 * filtre una lista que el navegador ya tiene entera sería añadir latencia
 * a cambio de nada.
 *
 * El carril es un contenedor con desplazamiento NATIVO y `scroll-snap`, no
 * un carrusel de JavaScript moviendo un `transform`. La diferencia importa:
 * así funciona el deslizamiento con el dedo y su inercia, la rueda del
 * ratón, el trackpad, el tabulador y las teclas de flecha —todo gratis— y
 * si el JavaScript no llega, el carril sigue desplazándose. Las flechas
 * solo añaden una comodidad para quien usa ratón; no son el mecanismo.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import type { ProjectSummary, Technology } from '../../lib/types';
import type { Dictionary } from '../../lib/i18n';

interface Props {
  projects: ProjectSummary[];
  technologies: Technology[];
  dict: Dictionary;
  projectBasePath: string;
}

export default function ProjectFilter({ projects, technologies, dict, projectBasePath }: Props) {
  const [active, setActive] = useState<string | null>(null);
  const rail = useRef<HTMLUListElement>(null);
  const [edges, setEdges] = useState({ start: true, end: false });

  const visible = useMemo(
    () =>
      active ? projects.filter((p) => p.technologies.some((t) => t.slug === active)) : projects,
    [projects, active],
  );

  /** Apaga la flecha que no lleva a ninguna parte. */
  const readEdges = useCallback(() => {
    const el = rail.current;
    if (!el) return;
    const max = el.scrollWidth - el.clientWidth;
    setEdges({ start: el.scrollLeft <= 1, end: el.scrollLeft >= max - 1 });
  }, []);

  useEffect(() => {
    const el = rail.current;
    if (!el) return;
    readEdges();
    el.addEventListener('scroll', readEdges, { passive: true });
    const observer = new ResizeObserver(readEdges);
    observer.observe(el);
    return () => {
      el.removeEventListener('scroll', readEdges);
      observer.disconnect();
    };
  }, [readEdges, visible.length]);

  // Al cambiar de filtro el carril vuelve al principio: quedarse a mitad de
  // un carril que ahora tiene otro contenido desorienta.
  useEffect(() => {
    rail.current?.scrollTo({ left: 0, behavior: 'auto' });
  }, [active]);

  /* ── Movimiento continuo ─────────────────────────────────────
     El carril avanza solo, despacio, y cambia de ritmo según lo que esté
     haciendo quien mira. No son dos estados sino una velocidad objetivo a
     la que se llega suavemente:

       nada encima      → velocidad completa
       cursor encima    → 30 %, para reconocer la presencia sin plantarse
       foco de teclado  → quieto
       dedo apoyado     → quieto
       pestaña oculta   → quieto

     Los dos últimos casos SÍ paran del todo, y es deliberado. Quien navega
     con el tabulador necesita que el elemento enfocado no se mueva, y quien
     arrastra con el dedo está dando su propia velocidad: sumarle la nuestra
     haría que el carril se le fuera de las manos.

     El cambio entre velocidades es progresivo. Un frenazo instantáneo se
     lee como un fallo; una desaceleración corta se lee como una respuesta.

     Y sobre `prefers-reduced-motion`: quien pidió menos movimiento no ve
     ninguno. El movimiento automático puede marear o dificultar la lectura.
     No se negocia ni se suaviza: no existe. */
  const [hovering, setHovering] = useState(false);
  const [held, setHeld] = useState(false);
  const [focused, setFocused] = useState(false);
  const carry = useRef(0);
  const factor = useRef(1);

  /* El anclaje se decide por lo que está haciendo quien mira, NO por la
     velocidad calculada dentro del bucle de animación. Atarlo al bucle
     significaría que si los fotogramas se ralentizan —una pestaña en
     segundo plano, un móvil con poca batería— el anclaje no volvería
     cuando hace falta. Aquí basta con saber si alguien tiene el carril
     agarrado o enfocado. */
  const stopped = held || focused;

  /* `prefers-reduced-motion` se lee DESPUÉS de montar, nunca durante el
     render. Consultarlo al renderizar produce un desajuste de hidratación:
     en el servidor no existe `window`, así que sale «false», y React
     conserva el valor del servidor en la hidratación inicial. El resultado
     era que quien pidió menos movimiento seguía viendo moverse el carril.
     Leerlo en un efecto fuerza un segundo render, que es lo que hace falta.
     El listener atiende además el cambio en caliente. */
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const apply = () => setReduced(query.matches);
    apply();
    query.addEventListener('change', apply);
    return () => query.removeEventListener('change', apply);
  }, []);

  const drifting = !stopped && !reduced;

  /* El carril solo se duplica cuando va a moverse solo. Con «menos
     movimiento» activado no hay bucle: se navega a mano, y ahí unas copias
     al final serían confusas en lugar de invisibles. Con una sola tarjeta
     tampoco hay nada que enlazar. */
  const looping = !reduced && visible.length > 1;

  useEffect(() => {
    const el = rail.current;
    if (!el) return;
    if (reduced) return;

    let frame = 0;
    let last = performance.now();
    const SPEED = 22; // píxeles por segundo a velocidad completa
    const HOVER_FACTOR = 0.3;
    const EASE_MS = 260; // lo que tarda en alcanzar la nueva velocidad

    const step = (now: number) => {
      const delta = Math.min(now - last, 100); // una pestaña que vuelve del fondo no debe dar un salto
      last = now;
      frame = requestAnimationFrame(step);

      const target = held || focused || document.hidden ? 0 : hovering ? HOVER_FACTOR : 1;
      factor.current += (target - factor.current) * Math.min(1, delta / EASE_MS);
      if (Math.abs(target - factor.current) < 0.01) factor.current = target;

      if (factor.current <= 0.01) return;

      const max = el.scrollWidth - el.clientWidth;
      if (max <= 0) return;

      // El avance se acumula: a esta velocidad cada fotograma vale menos de
      // medio píxel, y redondear en cada uno congelaría el carril.
      carry.current += (SPEED * factor.current * delta) / 1000;
      const whole = Math.floor(carry.current);
      if (whole < 1) return;
      carry.current -= whole;

      const next = el.scrollLeft + whole;

      if (looping) {
        // La lista está duplicada, así que la primera mitad y la segunda son
        // idénticas. Al pasar la mitad se resta esa distancia: el contenido
        // bajo la vista es exactamente el mismo, de modo que el salto no se
        // percibe y el carril parece no terminar nunca.
        const half = el.scrollWidth / 2;
        el.scrollLeft = next >= half ? next - half : next;
      } else {
        el.scrollLeft = next >= max - 1 ? 0 : next;
      }
    };

    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [hovering, held, focused, reduced, looping, visible.length]);

  /** Avanza o retrocede una tarjeta. */
  const nudge = (dir: -1 | 1) => {
    const el = rail.current;
    if (!el) return;
    // Un empujón manual manda: se frena para no pelear con el movimiento
    // automático, y este se reanuda solo cuando el cursor se va.
    setHeld(true);
    window.setTimeout(() => setHeld(false), 900);
    const card = el.querySelector('li');
    const step = card ? card.getBoundingClientRect().width + 24 : el.clientWidth * 0.8;

    if (looping) {
      // Con el carril en bucle las flechas nunca topan: pasada la mitad se
      // reposiciona antes de desplazar, así que desde la última tarjeta la
      // flecha derecha sigue llevando a la primera.
      const half = el.scrollWidth / 2;
      let from = el.scrollLeft + step * dir;
      if (from < 0) {
        el.scrollLeft += half;
        from += half;
      } else if (from >= half) {
        el.scrollLeft -= half;
        from -= half;
      }
      el.scrollTo({ left: from, behavior: reduced ? 'auto' : 'smooth' });
      return;
    }

    el.scrollBy({ left: step * dir, behavior: reduced ? 'auto' : 'smooth' });
    // El estado de las flechas lo mantiene el evento `scroll`, pero un
    // desplazamiento suave puede terminar sin un último evento. Una
    // comprobación al acabar la animación garantiza que la flecha del
    // extremo se apague siempre.
    window.setTimeout(readEdges, reduced ? 0 : 450);
  };

  /** Una tarjeta. `clone` marca las copias del carril infinito. */
  const renderCard = (project: ProjectSummary, clone: boolean) => (
    <li key={`${project.slug}${clone ? '-copia' : ''}`} className="card" aria-hidden={clone}>
      <a
        href={`${projectBasePath}/${project.slug}`}
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
        <div className="rail-wrap">
          <button
            type="button"
            className="rail-arrow rail-prev"
            onClick={() => nudge(-1)}
            disabled={!looping && edges.start}
            aria-label={dict.projects.scrollPrev}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M15 5l-7 7 7 7"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>

          <ul
            className={`rail ${drifting ? 'is-drifting' : ''}`}
            ref={rail}
            onPointerEnter={() => setHovering(true)}
            onPointerLeave={() => {
              setHovering(false);
              setHeld(false);
            }}
            onPointerDown={() => setHeld(true)}
            onPointerUp={() => setHeld(false)}
            onPointerCancel={() => setHeld(false)}
            onFocusCapture={() => setFocused(true)}
            onBlurCapture={() => setFocused(false)}
          >
            {visible.map((project) => renderCard(project, false))}
            {/* Segunda vuelta: el carril infinito se hace duplicando el
                contenido y saltando a la mitad cuando se llega al final. El
                salto es invisible porque en ese punto la pantalla muestra
                exactamente lo mismo.

                Las copias van con `aria-hidden` y sin tabulación: para un
                lector de pantalla o para quien navega con teclado hay CINCO
                proyectos, no diez. Duplicar el contenido visual no debe
                duplicar el contenido anunciado. */}
            {looping && visible.map((project) => renderCard(project, true))}
          </ul>

          <button
            type="button"
            className="rail-arrow rail-next"
            onClick={() => nudge(1)}
            disabled={!looping && edges.end}
            aria-label={dict.projects.scrollNext}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M9 5l7 7-7 7"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
