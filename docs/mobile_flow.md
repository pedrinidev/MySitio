# Flujo móvil

> Estado: **diseño aprobado** · Última actualización: 2026-09-10

---

## Nota sobre este documento

Las reglas del proyecto exigen `mobile_flow.md`. **Este sistema no incluye una aplicación móvil nativa**:
es un sitio web con backend. Por lo tanto, este documento cubre lo que sí aplica —la experiencia móvil
del sitio— y deja registrado explícitamente que las reglas de MVVM y Repository Pattern **no tienen
sujeto** aquí. Si en el futuro se añade una app nativa (por ejemplo, un cliente Android del blog),
este documento pasa a describir su arquitectura.

Se documenta la ausencia en lugar de dejar el archivo vacío o inventar una capa que no existe.

---

## 1. Mobile-first no es una opción

Un portafolio dirigido a reclutadores se abre **desde el teléfono**, muchas veces desde un enlace en
LinkedIn o WhatsApp. Es el escenario principal, no una degradación del escritorio.

Consecuencia práctica: cada sección se diseña primero en 375 px de ancho y después se expande.
El escritorio hereda del móvil, nunca al revés.

---

## 2. Puntos de corte

| Nombre | Ancho | Objetivo |
|---|---|---|
| `base` | 375–639 px | teléfono — diseño de una columna |
| `sm` | 640 px | teléfono grande |
| `md` | 768 px | tablet — grid de 2 columnas |
| `lg` | 1024 px | portátil — navegación completa |
| `xl` | 1280 px+ | escritorio — ancho máximo de contenido 1200 px |

---

## 3. Reglas de interacción táctil

- **Objetivo táctil mínimo: 44 × 44 px.** Sin excepciones, ni en los iconos sociales del pie.
- Ningún contenido esencial detrás de un `:hover` — en una pantalla táctil, `hover` no existe.
  Los efectos de las tarjetas de proyecto son decorativos; el enlace siempre es explícito.
- Áreas de pulsación separadas por al menos 8 px.
- Los modales de detalle de proyecto se convierten en **hoja inferior deslizable** (bottom sheet) por
  debajo de `md`, y se cierran deslizando hacia abajo.
- Los juegos se diseñan con controles táctiles desde el inicio: Snake con gestos de deslizamiento,
  no con flechas del teclado adaptadas a posteriori.

---

## 4. Animación en móvil

El estilo Apple depende del movimiento, y el movimiento es exactamente donde un teléfono de gama media
se rompe. Reglas:

- Animar **solo** `transform` y `opacity`. Nunca `width`, `height`, `top` o `left`: fuerzan
  recálculo de diseño en cada fotograma.
- `ScrollTrigger` con `scrub` se **desactiva** por debajo de `md`. En móvil, el contenido aparece con
  transiciones cortas y simples al entrar en pantalla.
- El parallax del hero se reduce a la mitad de amplitud en móvil.
- **`prefers-reduced-motion: reduce` desactiva todo**: sin desplazamiento, sin escala, sin parallax.
  El contenido aparece directamente. Es accesibilidad, no una preferencia estética.
- Objetivo: **60 fps sostenidos en un Android de gama media**, verificado en un dispositivo real
  —no solo en el emulador de Chrome.

---

## 5. Presupuesto de rendimiento en móvil

| Métrica | Objetivo | Por qué |
|---|---|---|
| LCP | < 1,5 s en 4G | por encima de 2,5 s, la gente cierra la pestaña |
| CLS | < 0,05 | todo `img` con `width`/`height` declarados |
| JS en la home | ≤ 120 KB comprimido | las islas cargan bajo demanda, no de entrada |
| Imágenes | AVIF/WebP, `loading="lazy"` salvo el hero | |
| Fuentes | `font-display: swap`, subconjunto latino, precargada la principal | |

**Carga de las islas:** solo `ProjectFilter` usa `client:load`. Los juegos, el dashboard de métricas y
el formulario usan `client:visible` — su JavaScript no se descarga hasta que el visitante se acerca a
ellos. Alguien que solo lee la home nunca paga el coste del motor de Snake.

---

## 6. Referencia: la app móvil del perfil

**MentePro** (Kotlin + Android SDK, publicada en Google Play) es la pieza móvil real del portafolio.
No forma parte de este sistema, pero se documenta aquí porque es el proyecto destacado del apartado
de proyectos y el caso de estudio principal: ciclo completo de desarrollo, firma, generación del
bundle y publicación en Google Play Console.

Su arquitectura interna se describe en su propio repositorio, no aquí.
