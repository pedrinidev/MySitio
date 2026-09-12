/**
 * Cliente de la API de Django.
 *
 * Se usa en dos momentos muy distintos y eso define su diseño:
 *
 * 1. **En el build (GitHub Actions).** Astro pide los datos para prerenderizar
 *    cada página. Si la API no responde, el build **debe fallar con estrépito**.
 *    Publicar un sitio con la sección de proyectos vacía es infinitamente peor
 *    que no publicar: el visitante concluye que el trabajo no existe.
 *
 * 2. **En el navegador (islas React).** Ahí un fallo NO puede tumbar la página:
 *    el dashboard muestra un aviso, el resto del sitio sigue intacto. Para eso
 *    está `fetchApiSafe`.
 */

import type {
  Category,
  Game,
  LiveMetrics,
  MetricSnapshot,
  Paginated,
  PostDetail,
  PostSummary,
  Profile,
  ProjectDetail,
  ProjectSummary,
  QuizQuestion,
  Score,
  Tag,
  Technology,
  Language,
} from './types';

const PUBLIC_API_URL = import.meta.env.PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

/**
 * Dirección de la API vista desde DENTRO del contenedor.
 *
 * En desarrollo con Docker, el servidor y el navegador no llegan a la API
 * por la misma puerta: dentro de la red de Compose es `api:8000`, y desde
 * el Mac es `localhost:8000`. Una sola variable no puede valer para los
 * dos — con `api:8000` el navegador no resuelve el nombre y toda llamada
 * del cliente falla; con `localhost:8000` es Astro quien no encuentra nada,
 * porque ese localhost es el del propio contenedor web.
 *
 * En producción no se define: la API pública es la misma URL para ambos.
 */
/* El `|| undefined` del final NO sobra. El Dockerfile declara
   `ARG INTERNAL_API_URL=` sin valor, así que en producción esta variable
   llega como cadena VACÍA, no ausente. Con `??` —que solo cae al respaldo
   con null o undefined— la cadena vacía se tomaba por buena, la URL base
   quedaba en "" y el build entero moría con un «Invalid URL» que no decía
   de dónde venía. */
const INTERNAL_API_URL =
  typeof process === 'undefined' ? undefined : process.env.INTERNAL_API_URL || undefined;

const API_URL = import.meta.env.SSR ? (INTERNAL_API_URL ?? PUBLIC_API_URL) : PUBLIC_API_URL;

/**
 * Token que exime al build del límite de peticiones de la API.
 *
 * NO lleva prefijo PUBLIC_ a propósito: así Astro no lo incrusta en el HTML
 * generado. Solo existe durante el build, en el proceso de Node.
 *
 * El `typeof process` NO es defensivo de más, es imprescindible. En el
 * navegador `process` no existe, y como esta constante se evalúa al
 * importar el módulo —no dentro de una función— el ReferenceError impedía
 * que el módulo llegara a cargarse. Con él caían las SEIS islas que
 * dependen de este archivo: formulario de contacto, los dos juegos, la
 * búsqueda del blog, el ranking y el panel de métricas. En producción el
 * fallo estaba oculto porque Vite elimina la rama al compilar; solo se
 * manifestaba en desarrollo, que es justo donde se prueba todo.
 */
const BUILD_TOKEN: string =
  import.meta.env.BUILD_API_TOKEN ??
  (typeof process === 'undefined' ? '' : (process.env.BUILD_API_TOKEN ?? ''));

/** El build no debe colgarse indefinidamente si la API deja de responder. */
const BUILD_TIMEOUT_MS = 15_000;

/**
 * Memoria de peticiones para el build.
 *
 * `getStaticPaths` y los componentes de página piden los mismos listados
 * varias veces: el despachador de rutas necesita todos los proyectos para
 * generar las rutas, y luego cada página vuelve a pedirlos. Sin esto, un
 * sitio de 20 páginas hace ~30 peticiones idénticas en pocos segundos —
 * lento, y suficiente para chocar contra el propio límite de la API.
 *
 * Vive solo mientras dura el proceso de build; en el navegador no se usa.
 */
const buildCache = new Map<string, Promise<unknown>>();

export class ApiUnavailableError extends Error {
  constructor(path: string, cause: unknown) {
    super(
      `No se pudo obtener ${path} desde ${API_URL}.\n` +
        `Causa: ${cause instanceof Error ? cause.message : String(cause)}\n\n` +
        `El build se detiene a propósito: publicar el sitio sin contenido es\n` +
        `peor que no publicarlo. Comprobá que la API esté en pie y accesible\n` +
        `desde el runner antes de reintentar.`,
    );
    this.name = 'ApiUnavailableError';
  }
}

function buildUrl(path: string, params: Record<string, string | number | undefined> = {}): string {
  const url = new URL(`${API_URL}${path}`);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') url.searchParams.set(key, String(value));
  }
  return url.toString();
}

/**
 * Petición que FALLA el build si algo va mal. Para usar en tiempo de compilación.
 */
export async function fetchApi<T>(
  path: string,
  params: Record<string, string | number | undefined> = {},
): Promise<T> {
  const url = buildUrl(path, params);

  const cached = buildCache.get(url);
  if (cached) return cached as Promise<T>;

  const pending = (async () => {
    try {
      const headers: Record<string, string> = { Accept: 'application/json' };
      if (BUILD_TOKEN) headers['X-Build-Token'] = BUILD_TOKEN;

      const response = await fetch(url, {
        headers,
        signal: AbortSignal.timeout(BUILD_TIMEOUT_MS),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status} ${response.statusText}`);
      }
      return (await response.json()) as T;
    } catch (cause) {
      // Se retira de la memoria para que un reintento posterior no reciba
      // el mismo fallo cacheado.
      buildCache.delete(url);
      throw new ApiUnavailableError(url, cause);
    }
  })();

  buildCache.set(url, pending);
  return pending;
}

/**
 * Petición tolerante a fallos. Para usar en el navegador, dentro de las islas.
 */
export async function fetchApiSafe<T>(
  path: string,
  params: Record<string, string | number | undefined> = {},
  init: RequestInit = {},
): Promise<{ data: T; error: null } | { data: null; error: string }> {
  try {
    const response = await fetch(buildUrl(path, params), {
      headers: { Accept: 'application/json', ...(init.headers ?? {}) },
      ...init,
    });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const body = await response.json();
        if (body?.detail) detail = body.detail;
      } catch {
        /* la respuesta no era JSON: nos quedamos con el código de estado */
      }
      return { data: null, error: detail };
    }
    if (response.status === 204) return { data: null as T, error: null };
    return { data: (await response.json()) as T, error: null };
  } catch (cause) {
    return { data: null, error: cause instanceof Error ? cause.message : 'Error de red' };
  }
}

/** POST tolerante a fallos, para formularios y envío de puntuaciones. */
export async function postApiSafe<T>(
  path: string,
  body: unknown,
  params: Record<string, string | number | undefined> = {},
) {
  return fetchApiSafe<T>(path, params, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/* ── Lecturas usadas en tiempo de build ──────────────────────────── */

export const getProfile = (lang: Language) => fetchApi<Profile>('/profile/', { lang });

export const getTechnologies = (lang: Language) =>
  fetchApi<Technology[]>('/technologies/', { lang });

export const getProjects = (lang: Language) =>
  fetchApi<Paginated<ProjectSummary>>('/projects/', { lang, page_size: 50 }).then((r) => r.results);

export const getProject = (slug: string, lang: Language) =>
  fetchApi<ProjectDetail>(`/projects/${slug}/`, { lang });

export const getPosts = (lang: Language) =>
  fetchApi<Paginated<PostSummary>>('/blog/posts/', { lang, page_size: 50 }).then((r) => r.results);

export const getPost = (slug: string, lang: Language) =>
  fetchApi<PostDetail>(`/blog/posts/${slug}/`, { lang });

export const getCategories = (lang: Language) =>
  fetchApi<Category[]>('/blog/categories/', { lang });

export const getTags = (lang: Language) => fetchApi<Tag[]>('/blog/tags/', { lang });

export const getGames = (lang: Language) => fetchApi<Game[]>('/games/', { lang });

export const getQuizQuestions = (slug: string, lang: Language) =>
  fetchApi<QuizQuestion[]>(`/games/${slug}/questions/`, { lang });

/* ── Lecturas del navegador ──────────────────────────────────────── */

export const fetchLiveMetrics = () => fetchApiSafe<LiveMetrics>('/metrics/live/');

export const fetchMetricHistory = (hours = 24) =>
  fetchApiSafe<MetricSnapshot[]>('/metrics/history/', { hours });

export const fetchLeaderboard = (slug: string, limit = 10) =>
  fetchApiSafe<Score[]>(`/games/${slug}/scores/`, { limit });

export const startGameSession = (slug: string) =>
  postApiSafe<{ token: string; expires_in: number }>(`/games/${slug}/session/`, {});

export interface ScoreSubmitResponse {
  score: number;
  correct: number;
  total: number;
  nickname: string;
  rank: number;
  details: {
    question: number;
    chosen_option: number | null;
    correct_option: number | null;
    was_correct: boolean;
    explanation: string;
  }[];
}

/** El idioma se envía porque el repaso del cuestionario viene traducido. */
export const submitScore = (slug: string, payload: unknown, lang?: Language) =>
  postApiSafe<ScoreSubmitResponse>(`/games/${slug}/scores/submit/`, payload, { lang });

export const searchPosts = (query: string, lang: Language) =>
  fetchApiSafe<Paginated<PostSummary>>('/blog/posts/', { q: query, lang, page_size: 20 });

export const sendContactMessage = (payload: unknown) =>
  postApiSafe<{ detail: string }>('/contact/', payload);
