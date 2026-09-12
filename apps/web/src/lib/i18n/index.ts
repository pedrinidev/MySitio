/**
 * Cadenas de interfaz.
 *
 * Viven en JSON dentro del repositorio, NO en la base de datos. Pagar una
 * consulta a Django por la palabra «Enviar» no tiene ningún sentido: son
 * literales que cambian cuando cambia el código, no cuando cambia el
 * contenido. El contenido real (proyectos, posts, biografía) sí viene del
 * admin. Ver docs/architecture.md, sección 6.
 */

import es from './es.json';
import en from './en.json';
import type { Language } from '../types';

const DICTIONARIES = { es, en } as const;

export type Dictionary = typeof es;

export const LANGUAGES: Language[] = ['es', 'en'];
export const DEFAULT_LANGUAGE: Language = 'es';

export function isLanguage(value: unknown): value is Language {
  return value === 'es' || value === 'en';
}

/** Diccionario completo del idioma pedido. */
export function useTranslations(lang: Language): Dictionary {
  return DICTIONARIES[lang] ?? DICTIONARIES[DEFAULT_LANGUAGE];
}

/**
 * Segmentos de ruta traducidos.
 *
 * Las URLs se traducen (`/es/proyectos/` y `/en/projects/`) porque son parte
 * del contenido: una URL en español posiciona mejor en búsquedas en español
 * y le dice al visitante que está en el sitio correcto.
 */
export const ROUTES = {
  es: {
    projects: 'proyectos',
    blog: 'blog',
    games: 'juegos',
    about: 'sobre-mi',
    contact: 'contacto',
  },
  en: { projects: 'projects', blog: 'blog', games: 'games', about: 'about', contact: 'contact' },
} as const;

/** Construye una URL absoluta dentro del sitio para el idioma dado. */
export function localePath(lang: Language, ...segments: string[]): string {
  const path = segments.filter(Boolean).join('/');
  return path ? `/${lang}/${path}` : `/${lang}/`;
}

/** Ruta equivalente en el otro idioma, para el selector. */
export function alternateLanguage(lang: Language): Language {
  return lang === 'es' ? 'en' : 'es';
}

/** Formatea una fecha ISO en el idioma indicado. */
export function formatDate(iso: string, lang: Language): string {
  return new Date(iso).toLocaleDateString(lang === 'es' ? 'es-BO' : 'en-GB', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

/** Convierte segundos de uptime en algo legible: «12 d 4 h». */
export function formatUptime(seconds: number, dict: Dictionary): string {
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  if (days > 0) return `${days} ${dict.metrics.days} ${hours} ${dict.metrics.hours}`;
  if (hours > 0) return `${hours} ${dict.metrics.hours} ${minutes} ${dict.metrics.minutes}`;
  return `${minutes} ${dict.metrics.minutes}`;
}
