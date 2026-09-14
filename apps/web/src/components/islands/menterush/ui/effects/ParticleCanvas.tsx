import { useEffect, useRef } from 'react'
import styles from './effects.module.css'

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  life: number
  maxLife: number
  size: number
  rotation: number
  spin: number
  color: string
}

const GRAVITY = 0.05
const FRICTION = 0.988

/** Tope de píxeles del lienzo (~10 MB de memoria gráfica). */
const MAX_CANVAS_PIXELS = 2_500_000

/**
 * Paleta de fiesta. Se mezcla con el acento de la racha para que la celebración
 * sea de colores y no un chorro monocromo del color del tier.
 */
const CONFETTI = ['#ffd93d', '#ff6b9d', '#4ecdc4', '#a78bfa', '#ffa62b', '#6bcb77', '#ffffff']

/** `matchMedia` no existe en algunos WebViews ni en entornos de test. */
function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Dibuja una estrella de cinco puntas centrada en (x, y). */
function drawStar(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number,
  rotation: number,
): void {
  const spikes = 5
  const inner = radius * 0.45

  ctx.beginPath()
  for (let i = 0; i < spikes * 2; i++) {
    const r = i % 2 === 0 ? radius : inner
    const angle = (i * Math.PI) / spikes + rotation
    const px = x + Math.cos(angle) * r
    const py = y + Math.sin(angle) * r
    if (i === 0) ctx.moveTo(px, py)
    else ctx.lineTo(px, py)
  }
  ctx.closePath()
  ctx.fill()
}

/**
 * Estrellas de colores que salen disparadas al acertar.
 *
 * El bucle de render **solo corre mientras hay estrellas vivas**: en reposo el
 * componente no consume un solo frame, que es lo que permite mantener 60 fps
 * durante la secuencia de números.
 *
 * Cada cambio de `burstKey` dispara una celebración.
 */
export function ParticleCanvas({
  burstKey,
  color,
  intensity = 1,
}: {
  burstKey: number
  color: string
  intensity?: number
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<Particle[]>([])
  const frameRef = useRef(0)
  const runningRef = useRef(false)
  const colorRef = useRef(color)
  colorRef.current = color
  // La intensidad también por referencia. Estaba en las dependencias del
  // efecto de abajo, y como vale el tier de combo, ROMPER una racha la
  // cambiaba (2 → 0) y disparaba una celebración al equivocarse. A la
  // siguiente falta ya no saltaba, porque el tier seguía en 0: justo el
  // comportamiento errático que se veía.
  const intensityRef = useRef(intensity)
  intensityRef.current = intensity

  // Tamaño físico del canvas, ajustado a la densidad de pantalla.
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    // ADAPTADO: se mide el PROPIO lienzo, no la ventana.
    //
    // El original usaba `window.innerWidth/Height` porque el juego ocupaba
    // la pantalla entera y ambas cosas coincidían. Dentro del portafolio no:
    // el lienzo mide unos 430x780 mientras la ventana mide 1280x800, así que
    // el búfer salía cuatro veces más grande de lo necesario y las estrellas
    // nacían en un punto que ni siquiera cae dentro de la caja.
    const resize = () => {
      const { clientWidth: ancho, clientHeight: alto } = canvas
      if (!ancho || !alto) return

      // Un lienzo grande con densidad 2 son decenas de MB para un efecto de
      // un segundo. Se acota el área total: en cajas pequeñas no cambia
      // nada, y en grandes las estrellas salen algo más suaves, que en
      // formas en movimiento y que se desvanecen no se aprecia.
      const byArea = Math.sqrt(MAX_CANVAS_PIXELS / Math.max(ancho * alto, 1))
      const dpr = Math.min(window.devicePixelRatio || 1, 2, byArea)

      canvas.width = Math.round(ancho * dpr)
      canvas.height = Math.round(alto * dpr)
      const ctx = canvas.getContext('2d')
      ctx?.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    resize()
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', resize)
      return () => window.removeEventListener('resize', resize)
    }
    const observador = new ResizeObserver(resize)
    observador.observe(canvas)
    return () => observador.disconnect()
  }, [])

  useEffect(() => {
    if (burstKey === 0 || prefersReducedMotion()) return

    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return

    // El centro del LIENZO, no el de la ventana: es lo que hace que la
    // celebración ocurra donde está el juego y llene su contenedor.
    const originX = canvas.clientWidth / 2
    const originY = canvas.clientHeight / 2
    const fuerza = intensityRef.current
    const count = Math.round(46 + fuerza * 20)
    // El acento entra en el sorteo, así que la racha tiñe la celebración sin
    // apoderarse de ella.
    const palette = [...CONFETTI, colorRef.current, colorRef.current]

    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2
      const speed = 2.6 + Math.random() * (4 + fuerza * 1.4)
      const maxLife = 52 + Math.random() * 42
      particlesRef.current.push({
        x: originX,
        y: originY,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 1.6,
        life: maxLife,
        maxLife,
        size: 5 + Math.random() * 7,
        rotation: Math.random() * Math.PI * 2,
        spin: (Math.random() - 0.5) * 0.28,
        color: palette[Math.floor(Math.random() * palette.length)] as string,
      })
    }

    if (runningRef.current) return
    runningRef.current = true

    const render = () => {
      ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight)

      const alive: Particle[] = []
      for (const p of particlesRef.current) {
        p.vx *= FRICTION
        p.vy = p.vy * FRICTION + GRAVITY
        p.x += p.vx
        p.y += p.vy
        p.rotation += p.spin
        p.life -= 1

        if (p.life > 0) {
          // Se apagan en el último tercio de vida, no de golpe.
          ctx.globalAlpha = Math.min(1, (p.life / p.maxLife) * 2.2)
          ctx.fillStyle = p.color
          drawStar(ctx, p.x, p.y, p.size, p.rotation)
          alive.push(p)
        }
      }
      ctx.globalAlpha = 1
      particlesRef.current = alive

      if (alive.length > 0) {
        frameRef.current = requestAnimationFrame(render)
      } else {
        // Sin estrellas vivas se detiene el bucle por completo.
        runningRef.current = false
        ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight)
      }
    }

    frameRef.current = requestAnimationFrame(render)
    // SOLO `burstKey`: una celebración ocurre cuando se acierta, y por
    // ninguna otra razón.
  }, [burstKey])

  useEffect(() => {
    return () => {
      cancelAnimationFrame(frameRef.current)
      runningRef.current = false
      particlesRef.current = []
    }
  }, [])

  return <canvas ref={canvasRef} className={styles.canvas} aria-hidden="true" />
}
