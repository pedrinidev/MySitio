import type { CSSProperties } from 'react'
import styles from './components.module.css'

/** Cuánto ocupa una cifra respecto a su tamaño de fuente.
 *
 * ADAPTADO: era 0.8 y se quedaba corto —la tipografía salía un tercio más
 * pequeña de lo que cabía— pero el valor correcto no es cualquiera: hay que
 * medirlo CON `tabular-nums` puesto. Las cifras tabulares son más anchas que
 * las proporcionales, y medirlas sin esa propiedad da 0.53 en vez de 0.68.
 *
 * Con 0.53 los números de dos cifras pedían 450px dentro de 430 útiles: al
 * desbordar, el centrado `safe` los alinea a la izquierda y el segundo
 * dígito quedaba recortado por la derecha.
 *
 *     medido a 353px de fuente, con tabular-nums:  «12» = 450px de caja
 *     avance por cifra = (450 + 2x14.1) / 2 = 239px  ->  239/353 = 0.677
 */
const DIGIT_RATIO = 0.68
/** El signo menos es más estrecho que una cifra (valor afinado midiendo). */
const SIGN_RATIO = 0.7
/** Porcentaje del ancho del CONTENEDOR que debe llenar el número.
 *
 * ADAPTADO: era 85. Medido dentro del portafolio, el escenario da 414x698 y
 * el número se quedaba en 348px de ancho y 245 de alto: sobraban 453px de
 * alto sin usar. Un 92 aprovecha el hueco dejando 16px a cada lado, que
 * basta para que no roce. */
const TARGET_WIDTH_PCT = 92

/**
 * El número de la secuencia a pantalla completa. La `key` la pone quien lo usa
 * para forzar el remontaje y que la animación de entrada se repita en cada
 * número, incluso si se repite el valor.
 *
 * El tamaño se calcula para que cualquier número —una cifra, dos, o dos con
 * signo— llene lo mismo de ancho. El límite en alto evita que en apaisado,
 * donde sobra ancho, el número se salga por arriba.
 *
 * ADAPTADO: las unidades son del CONTENEDOR (`cqw`/`cqh`), no del viewport.
 * Con `vw` este cálculo pedía, para dos cifras, un 53% del ANCHO DE LA
 * VENTANA: 678 px de tipografía dentro de una caja de 430. El «12» se salía
 * por la derecha. La conversión del resto del CSS no alcanzaba aquí porque
 * estas medidas se ponen en línea desde JavaScript.
 */
export function BigNumber({ value }: { value: number }) {
  const digits = Math.abs(value).toString().length
  const units = digits + (value < 0 ? SIGN_RATIO : 0)

  const byWidth = Math.round(TARGET_WIDTH_PCT / (DIGIT_RATIO * units))
  // ADAPTADO: el tope de alto sube de 68 a 78.
  //
  // Estaba calibrado para una pantalla de móvil, donde el escenario ocupa
  // bastante menos que el viewport por culpa de las barras del navegador.
  // Aquí el escenario es el 87% del contenedor, así que con 68 el límite lo
  // ponía el alto y una sola cifra se quedaba pequeña pese a sobrar sitio.
  const byHeight = Math.max(54, Math.round(78 - (units - 1) * 6))

  return (
    <div
      className={`${styles.bigNumber} ${value < 0 ? styles.negative : ''} tabular`}
      // Las tres apuntan al contenedor. `--num-alto-seguro` existía para el
      // `svh` de iOS —la altura real con las barras del navegador— pero un
      // contenedor no tiene barras: se le da el mismo valor para no tocar la
      // hoja de estilos, que elige entre las dos según el soporte.
      style={
        {
          '--num-ancho': `${byWidth}cqw`,
          '--num-alto': `${byHeight}cqh`,
          '--num-alto-seguro': `${byHeight}cqh`,
        } as CSSProperties
      }
    >
      {value}
    </div>
  )
}
