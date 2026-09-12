/**
 * Identidad de la marca.
 *
 * Vive en una constante y no repetida en cada página porque ya pasó una vez:
 * el nombre estaba copiado a mano en nueve archivos, se cambió la cabecera y
 * los `<title>` se quedaron con el anterior. Un solo sitio donde tocarlo.
 *
 * `SITE_NAME` es la MARCA, la que va en la pestaña del navegador.
 * El nombre legal de la persona sigue estando donde corresponde: el pie de
 * página, la sección «Sobre mí» y los datos estructurados de Schema.org,
 * que es lo que lee Google para saber quién hay detrás del sitio.
 */
export const SITE_NAME = 'PedriniDev';

/**
 * Nombre legal de la persona detrás de la marca.
 *
 * NO se muestra en ninguna página: la marca visible es `SITE_NAME`. Vive
 * únicamente en los datos estructurados de Schema.org, que es lo que lee
 * Google para vincular el sitio con una persona real. Sin esto, buscar el
 * nombre en un buscador no llevaría nunca a este sitio — y ese es
 * exactamente el camino que hace un reclutador con un CV en la mano.
 *
 * Es información que ya es pública: está en el CV que se reparte y en el
 * perfil de LinkedIn que el propio sitio enlaza. Aquí solo se le dice al
 * buscador que se trata de la misma persona.
 */
export const LEGAL_NAME = 'Pedro Mamani Tito';

/** Título de una página interior: «Proyectos — PedriniDev». */
export function pageTitle(section: string): string {
  return `${section} — ${SITE_NAME}`;
}
