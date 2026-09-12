/**
 * Animaciones — presets de GSAP centralizados.
 *
 * Todas las animaciones del sitio salen de aquí. Es intencional: cuando cada
 * componente inventa sus propias duraciones y curvas, el sitio deja de
 * sentirse como una sola pieza. Un único módulo también significa un único
 * sitio donde comprobar `prefers-reduced-motion`.
 *
 * Regla de rendimiento: se anima **solo `transform` y `opacity`**. Animar
 * `width`, `height`, `top` o `left` fuerza al navegador a recalcular el
 * diseño en cada fotograma, y en un Android de gama media eso son 20 fps.
 */

import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

/** Curva de referencia del sitio: arranque decidido, frenada larga. */
export const EASE = 'power3.out';

const MOBILE_BREAKPOINT = 768;

export function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function isMobileViewport(): boolean {
  return window.innerWidth < MOBILE_BREAKPOINT;
}

/**
 * Revela los elementos marcados con `data-reveal` al entrar en pantalla.
 *
 * Si el visitante pidió menos movimiento, no anima: hace visible el contenido
 * de inmediato. Nunca se deja un elemento invisible por no haberse disparado
 * la animación — es la forma más fácil de publicar una página en blanco.
 */
export function initRevealAnimations(root: ParentNode = document): void {
  const elements = root.querySelectorAll<HTMLElement>('[data-reveal]');
  if (elements.length === 0) return;

  if (prefersReducedMotion()) {
    gsap.set(elements, { opacity: 1, y: 0 });
    return;
  }

  const mobile = isMobileViewport();

  elements.forEach((element) => {
    const delay = Number(element.dataset.revealDelay ?? 0);
    gsap.to(element, {
      opacity: 1,
      y: 0,
      duration: mobile ? 0.5 : 0.9,
      delay,
      ease: EASE,
      scrollTrigger: {
        trigger: element,
        // Se dispara cuando al elemento le falta el 12 % de la ventana para
        // entrar: la animación ya está en marcha cuando el ojo llega.
        start: 'top 88%',
        once: true,
      },
    });
  });
}

/**
 * Entrada del hero: escalonada, sin scroll, al cargar la página.
 * Es lo primero que se ve, así que no se delega a ScrollTrigger.
 */
export function playHeroIntro(container: HTMLElement): void {
  const targets = container.querySelectorAll<HTMLElement>('[data-hero-item]');
  if (targets.length === 0) return;

  if (prefersReducedMotion()) {
    gsap.set(targets, { opacity: 1, y: 0 });
    return;
  }

  gsap.fromTo(
    targets,
    { opacity: 0, y: 40 },
    { opacity: 1, y: 0, duration: 1.1, ease: EASE, stagger: 0.09, delay: 0.1 },
  );
}

/**
 * Parallax vertical ligado al scroll.
 *
 * Se **desactiva por completo en móvil**: `scrub` obliga al navegador a
 * recalcular en cada evento de scroll, y en un teléfono compite con el
 * desplazamiento nativo produciendo tirones. En escritorio la amplitud es
 * deliberadamente pequeña — un parallax que se nota es un parallax mal hecho.
 */
export function initParallax(root: ParentNode = document): void {
  if (prefersReducedMotion() || isMobileViewport()) return;

  root.querySelectorAll<HTMLElement>('[data-parallax]').forEach((element) => {
    const strength = Number(element.dataset.parallax ?? 0.15);
    gsap.to(element, {
      yPercent: strength * 100,
      ease: 'none',
      scrollTrigger: {
        trigger: element.parentElement ?? element,
        start: 'top bottom',
        end: 'bottom top',
        scrub: 0.6,
      },
    });
  });
}

/**
 * Cuenta un número hasta su valor final cuando entra en pantalla.
 * Usado en las métricas del servidor y en los datos de los proyectos.
 */
export function initCounters(root: ParentNode = document): void {
  root.querySelectorAll<HTMLElement>('[data-counter]').forEach((element) => {
    const target = Number(element.dataset.counter ?? 0);
    const decimals = Number(element.dataset.counterDecimals ?? 0);

    if (prefersReducedMotion()) {
      element.textContent = target.toFixed(decimals);
      return;
    }

    const state = { value: 0 };
    gsap.to(state, {
      value: target,
      duration: 1.6,
      ease: 'power2.out',
      scrollTrigger: { trigger: element, start: 'top 90%', once: true },
      onUpdate: () => {
        element.textContent = state.value.toFixed(decimals);
      },
    });
  });
}

/** Arranca todas las animaciones de la página. Se llama una sola vez. */
export function initPageAnimations(): void {
  document.documentElement.classList.add('js');
  initRevealAnimations();
  initParallax();
  initCounters();

  const hero = document.querySelector<HTMLElement>('[data-hero]');
  if (hero) playHeroIntro(hero);
}

export { gsap, ScrollTrigger };
