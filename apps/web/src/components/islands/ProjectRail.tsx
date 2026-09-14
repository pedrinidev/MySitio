/**
 * Carril de proyectos que se desplaza solo.
 *
 * Es el mismo mecanismo que antes vivía en la página de Proyectos, movido
 * al inicio: ahí el movimiento aporta —es lo primero que se ve y da vida a
 * la portada— mientras que en el listado estorbaba a quien va a comparar
 * proyectos con calma. Ese listado ahora son tarjetas quietas.
 *
 * El desplazamiento es NATIVO con `scroll-snap`, no un `transform` movido
 * por JavaScript. Así funcionan el dedo y su inercia, la rueda, el
 * trackpad, el tabulador y las flechas del teclado sin escribir nada; y si
 * el JavaScript no llega, el carril se sigue pudiendo recorrer a mano.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ProjectSummary } from '../../lib/types';
import type { Dictionary } from '../../lib/i18n';
import ProjectCard from './ProjectCard';

interface Props {
  projects: ProjectSummary[];
  dict: Dictionary;
  projectBasePath: string;
}

export default function ProjectRail({ projects, dict, projectBasePath }: Props) {
  const rail = useRef<HTMLUListElement>(null);
  const [edges, setEdges] = useState({ start: true, end: false });

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
  }, [readEdges, projects.length]);

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
  const looping = !reduced && projects.length > 1;

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
  }, [hovering, held, focused, reduced, looping, projects.length]);

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

  if (projects.length === 0) return null;

  return (
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
        {projects.map((project) => (
          <ProjectCard key={project.slug} project={project} basePath={projectBasePath} />
        ))}
        {/* Segunda vuelta: el bucle infinito se hace duplicando el contenido
            y saltando a la mitad al llegar al final. El salto es invisible
            porque en ese punto la pantalla muestra exactamente lo mismo.

            Las copias van con `aria-hidden` y sin tabulación: para un lector
            de pantalla hay CINCO proyectos, no diez. */}
        {looping &&
          projects.map((project) => (
            <ProjectCard
              key={`${project.slug}-copia`}
              project={project}
              basePath={projectBasePath}
              clone
            />
          ))}
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
  );
}
