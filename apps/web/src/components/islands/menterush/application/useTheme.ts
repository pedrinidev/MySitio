import { useEffect, useState } from 'react'
import type { ThemePreference } from '../data'

export type ResolvedTheme = 'light' | 'dark'

/**
 * ADAPTADO: aquí el tema lo manda el SITIO, no el juego.
 *
 * En MenteRush como aplicación suelta este hook escribía `data-theme` en el
 * documento y el juego traía su propio interruptor. Dentro del portafolio
 * eso sobra y molesta: la página ya tiene un botón de claro/oscuro en la
 * cabecera, y dos interruptores para lo mismo en la misma pantalla son una
 * trampa —además de que escribir en la raíz cambiaría el tema del sitio
 * entero.
 *
 * Así que ahora solo OBSERVA lo que el sitio decide: el atributo
 * `data-theme` de la raíz si el visitante eligió, y `prefers-color-scheme`
 * si no. El botón propio del juego se quitó de las pantallas.
 *
 * El argumento se conserva para no cambiar la firma que espera
 * `useGameEngine`, pero se ignora a propósito.
 */
function temaDelSitio(): ResolvedTheme {
  if (typeof document === 'undefined') return 'dark'

  const elegido = document.documentElement.getAttribute('data-theme')
  if (elegido === 'light' || elegido === 'dark') return elegido

  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return 'dark'
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

export function useTheme(_preference: ThemePreference): ResolvedTheme {
  // Arranca en 'dark' a propósito, que es lo que pinta el servidor: leer el
  // tema real aquí produciría un valor distinto al del HTML entregado y
  // React, al hidratar, se queda con el del servidor en vez de corregirlo.
  // El valor bueno lo pone el efecto de abajo en cuanto el componente vive.
  const [tema, setTema] = useState<ResolvedTheme>('dark')

  useEffect(() => {
    if (typeof document === 'undefined') return
    const releer = () => setTema(temaDelSitio())
    releer()

    // Dos fuentes: el botón del sitio, que escribe el atributo, y el sistema
    // operativo cuando nadie eligió nada.
    const observador = new MutationObserver(releer)
    observador.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    })

    const consulta = window.matchMedia?.('(prefers-color-scheme: light)')
    consulta?.addEventListener('change', releer)

    return () => {
      observador.disconnect()
      consulta?.removeEventListener('change', releer)
    }
  }, [])

  return tema
}
