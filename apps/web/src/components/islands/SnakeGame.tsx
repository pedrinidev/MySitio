/**
 * Snake sobre canvas.
 *
 * Tres decisiones que definen el componente:
 *
 * 1. **Bucle de tiempo fijo con acumulador.** La serpiente avanza cada N
 *    milisegundos, no cada fotograma. Atar el movimiento a `requestAnimationFrame`
 *    haría que el juego fuese el doble de rápido en una pantalla de 120 Hz.
 * 2. **Controles táctiles de primera clase.** Se diseñan a la vez que el
 *    teclado, no como parche: en un teléfono no hay flechas.
 * 3. **La puntuación la valida el servidor.** El navegador la calcula, pero
 *    el backend rechaza lo imposible y exige un token de un solo uso.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { startGameSession, submitScore } from '../../lib/api';
import type { Dictionary } from '../../lib/i18n';

interface Props {
  slug: string;
  dict: Dictionary;
}

const GRID = 20;

/* ── Ritmo ───────────────────────────────────────────────────────────
   La partida empieza despacio y se acelera con cada bocado. Arrancar a la
   velocidad de crucero castiga al que juega por primera vez —que es casi
   todo el mundo que llega a un portafolio— y acelerar es lo que convierte
   una partida larga en algo tenso en lugar de repetitivo.

   170 ms es cómodo para orientarse; 80 ms es rápido pero todavía jugable.
   A 4 ms por bocado se llega al tope tras unas 22 comidas: lo bastante
   lejos como para que la aceleración se note poco a poco y no de golpe. */
const START_TICK_MS = 170;
const MIN_TICK_MS = 80;
const SPEEDUP_PER_FOOD = 4;
const INITIAL_LENGTH = 3;

/**
 * Víbora quieta que se pinta antes de empezar.
 *
 * Un tablero sin partida no tiene nada que enseñar: quedaba un rectángulo
 * vacío que parecía un fallo de carga. Con una víbora dibujada se entiende
 * de qué va el juego sin leer las instrucciones, y la sección deja de tener
 * un hueco al lado de MenteRush, que en reposo sí muestra contenido.
 *
 * El recorrido tiene curvas a propósito: una línea recta no se distingue de
 * una barra de progreso.
 */
const DEMO_SNAKE: Point[] = [
  { x: 14, y: 5 },
  { x: 13, y: 5 },
  { x: 12, y: 5 },
  { x: 11, y: 5 },
  { x: 10, y: 5 },
  { x: 9, y: 5 },
  { x: 8, y: 5 },
  { x: 8, y: 6 },
  { x: 8, y: 7 },
  { x: 8, y: 8 },
  { x: 9, y: 8 },
  { x: 10, y: 8 },
  { x: 11, y: 8 },
  { x: 12, y: 8 },
  { x: 13, y: 8 },
  { x: 13, y: 9 },
  { x: 13, y: 10 },
  { x: 12, y: 10 },
  { x: 11, y: 10 },
  { x: 10, y: 10 },
  { x: 9, y: 10 },
  { x: 8, y: 10 },
  { x: 7, y: 10 },
  { x: 6, y: 10 },
  { x: 6, y: 11 },
  { x: 6, y: 12 },
  { x: 7, y: 12 },
  { x: 8, y: 12 },
  { x: 9, y: 12 },
];

/** La comida, delante de la cabeza: sugiere hacia dónde va. */
const DEMO_FOOD: Point = { x: 17, y: 5 };

/** Milisegundos por paso según lo larga que sea la víbora. */
function tickInterval(length: number): number {
  return Math.max(MIN_TICK_MS, START_TICK_MS - (length - INITIAL_LENGTH) * SPEEDUP_PER_FOOD);
}

const SWIPE_THRESHOLD = 24;

type Point = { x: number; y: number };
type Phase = 'idle' | 'playing' | 'over' | 'saving' | 'saved';

const OPPOSITE: Record<string, string> = { up: 'down', down: 'up', left: 'right', right: 'left' };
const VECTORS: Record<string, Point> = {
  up: { x: 0, y: -1 },
  down: { x: 0, y: 1 },
  left: { x: -1, y: 0 },
  right: { x: 1, y: 0 },
};

export default function SnakeGame({ slug, dict }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [score, setScore] = useState(0);
  const [nickname, setNickname] = useState('');
  const [rank, setRank] = useState<number | null>(null);

  // El estado del juego vive en refs, no en useState: cambia hasta nueve
  // veces por segundo y provocar un re-render de React en cada tick sería
  // desperdiciar trabajo para redibujar un canvas que ya pintamos a mano.
  const snake = useRef<Point[]>(DEMO_SNAKE.map((p) => ({ ...p })));
  // Posiciones ANTES del último paso. Con ellas y las actuales se interpola
  // en cada fotograma: sin esto la víbora salta de casilla en casilla nueve
  // veces por segundo, que es exactamente lo que la hacía parecer una fila
  // de cuadrados en vez de un bicho que se desliza.
  const prevSnake = useRef<Point[]>([]);
  const food = useRef<Point>({ ...DEMO_FOOD });
  // Destello circular al comer: posición y momento en que se disparó.
  const eaten = useRef<{ x: number; y: number; at: number } | null>(null);
  // Colores leídos del CSS una sola vez por partida: getComputedStyle en
  // cada fotograma forzaría un recálculo de estilos sesenta veces por segundo.
  const palette = useRef({
    head: '#2997ff',
    tail: '#1d4ed8',
    food: '#ff9f0a',
    grid: 'rgba(255,255,255,0.04)',
    eye: '#ffffff',
    glow: 'rgba(41,151,255,0.55)',
    sheen: 'rgba(255,255,255,0.16)',
    foodLight: '#ffd48a',
    foodDark: '#b45309',
    leaf: '#34d399',
    headLight: '#7dc2ff',
  });
  const direction = useRef('right');
  const queued = useRef('right');
  const startedAt = useRef(0);
  const tokenRef = useRef<string | null>(null);
  const scoreRef = useRef(0);
  // Densidad de la pantalla. Sin esto el canvas dibuja 480 píxeles reales y
  // el navegador los estira sobre los ~1000 físicos de una pantalla Retina:
  // todo sale borroso y con el borde dentado. Es la causa principal de que
  // el juego pareciera «de píxeles».
  const dpr = useRef(1);

  const placeFood = useCallback(() => {
    let candidate: Point;
    do {
      candidate = { x: Math.floor(Math.random() * GRID), y: Math.floor(Math.random() * GRID) };
    } while (snake.current.some((part) => part.x === candidate.x && part.y === candidate.y));
    food.current = candidate;
  }, []);

  /**
   * Ajusta el búfer del canvas al tamaño que ocupa en pantalla, multiplicado
   * por la densidad del dispositivo.
   *
   * Se limita a 2x: por encima el coste de rellenar píxeles crece al cuadrado
   * y la diferencia ya no se aprecia.
   */
  const setupCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const wrap = canvas?.parentElement;
    if (!canvas || !wrap) return;
    const size = Math.round(wrap.clientWidth);
    if (size === 0) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    dpr.current = ratio;
    canvas.width = Math.round(size * ratio);
    canvas.height = Math.round(size * ratio);
  }, []);

  /** Lee la paleta del CSS. Se llama al empezar la partida, no por fotograma. */
  const readPalette = useCallback(() => {
    const wrap = canvasRef.current?.parentElement;
    if (!wrap) return;
    const s = getComputedStyle(wrap);
    const pick = (name: string, fallback: string) => s.getPropertyValue(name).trim() || fallback;
    palette.current = {
      head: pick('--snake-head', '#2997ff'),
      tail: pick('--snake-tail', '#1d4ed8'),
      food: pick('--snake-food', '#ff9f0a'),
      grid: pick('--snake-grid', 'rgba(255,255,255,0.04)'),
      eye: pick('--snake-eye', '#ffffff'),
      glow: pick('--snake-glow', 'rgba(41,151,255,0.55)'),
      sheen: pick('--snake-sheen', 'rgba(255,255,255,0.16)'),
      foodLight: pick('--snake-food-light', '#ffd48a'),
      foodDark: pick('--snake-food-dark', '#b45309'),
      leaf: pick('--snake-leaf', '#34d399'),
      headLight: pick('--snake-head-light', '#7dc2ff'),
    };
  }, []);

  /**
   * Pinta un fotograma.
   *
   * `alpha` es la fracción transcurrida del paso actual (0 a 1). El estado
   * del juego sigue siendo discreto —la víbora ocupa casillas enteras— pero
   * lo que se dibuja va interpolado entre la posición anterior y la nueva.
   * Es la diferencia entre un juego que da tirones y uno que se desliza.
   */
  const draw = useCallback((alpha = 1) => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return;

    const {
      head: headColor,
      tail: tailColor,
      food: foodColor,
      grid: gridColor,
      eye: eyeColor,
      glow: glowColor,
      sheen: sheenColor,
      foodLight,
      foodDark,
      leaf: leafColor,
      headLight,
    } = palette.current;

    // Se dibuja en píxeles CSS y el escalado a píxeles físicos lo hace la
    // transformación: la geometría no cambia con la densidad de pantalla,
    // solo la nitidez.
    context.setTransform(dpr.current, 0, 0, dpr.current, 0, 0);
    const size = canvas.width / dpr.current;
    const cell = size / GRID;
    const now = performance.now();

    context.clearRect(0, 0, size, size);

    // ── Cuadrícula ───────────────────────────────────────────────
    // Un punto tenue en cada cruce. Da noción de tablero y de escala sin
    // competir con nada; sobre un fondo liso la víbora parecía flotar.
    context.fillStyle = gridColor;
    for (let gx = 1; gx < GRID; gx++) {
      for (let gy = 1; gy < GRID; gy++) {
        context.beginPath();
        context.arc(gx * cell, gy * cell, Math.max(1, cell * 0.045), 0, Math.PI * 2);
        context.fill();
      }
    }

    // ── Comida ───────────────────────────────────────────────────
    // Late despacio y tiene un halo: es el único objetivo de la pantalla y
    // tiene que encontrarse de un vistazo, sin llegar a parpadear.
    const fx = (food.current.x + 0.5) * cell;
    const fy = (food.current.y + 0.5) * cell;
    const pulse = 1 + Math.sin(now / 320) * 0.07;
    const radius = cell * 0.34 * pulse;

    const halo = context.createRadialGradient(fx, fy, radius * 0.3, fx, fy, radius * 3.4);
    halo.addColorStop(0, foodColor);
    halo.addColorStop(1, 'transparent');
    context.globalAlpha = 0.32;
    context.fillStyle = halo;
    context.beginPath();
    context.arc(fx, fy, radius * 3.4, 0, Math.PI * 2);
    context.fill();
    context.globalAlpha = 1;

    // Degradado esférico en vez de un relleno plano: claro arriba a la
    // izquierda, oscuro abajo a la derecha. Un disco de un solo color se
    // lee como una mancha; con esta luz se lee como un objeto redondo.
    const esfera = context.createRadialGradient(
      fx - radius * 0.35,
      fy - radius * 0.4,
      radius * 0.1,
      fx,
      fy,
      radius * 1.15,
    );
    esfera.addColorStop(0, foodLight);
    esfera.addColorStop(0.45, foodColor);
    esfera.addColorStop(1, foodDark);
    context.fillStyle = esfera;
    context.beginPath();
    context.arc(fx, fy, radius, 0, Math.PI * 2);
    context.fill();

    // Hojita. La silueta se reconoce como fruta antes de que el ojo llegue
    // a procesar el color, que es lo que hace falta cuando hay que
    // localizarla de un vistazo mientras la víbora avanza.
    context.save();
    context.translate(fx + radius * 0.18, fy - radius * 0.92);
    context.rotate(-0.5);
    context.fillStyle = leafColor;
    context.beginPath();
    context.ellipse(0, 0, radius * 0.42, radius * 0.2, 0, 0, Math.PI * 2);
    context.fill();
    context.restore();

    context.fillStyle = 'rgba(255,255,255,0.7)';
    context.beginPath();
    context.ellipse(
      fx - radius * 0.32,
      fy - radius * 0.36,
      radius * 0.24,
      radius * 0.17,
      -0.6,
      0,
      Math.PI * 2,
    );
    context.fill();

    // ── Destello al comer ────────────────────────────────────────
    if (eaten.current) {
      const age = (now - eaten.current.at) / 420;
      if (age >= 1) {
        eaten.current = null;
      } else {
        context.globalAlpha = (1 - age) * 0.5;
        context.strokeStyle = foodColor;
        context.lineWidth = cell * 0.12 * (1 - age);
        context.beginPath();
        context.arc(
          (eaten.current.x + 0.5) * cell,
          (eaten.current.y + 0.5) * cell,
          cell * (0.3 + age * 1.1),
          0,
          Math.PI * 2,
        );
        context.stroke();
        context.globalAlpha = 1;
      }
    }

    // ── Víbora ───────────────────────────────────────────────────
    const body = snake.current;
    if (body.length === 0) return;

    const prev = prevSnake.current;
    const at = (i: number) => {
      const cur = body[i];
      const before = prev[i] ?? cur;
      return {
        x: (before.x + (cur.x - before.x) * alpha + 0.5) * cell,
        y: (before.y + (cur.y - before.y) * alpha + 0.5) * cell,
      };
    };

    // El cuerpo es UN SOLO trazo, no una serie de tramos.
    //
    // Antes se pintaba segmento a segmento, cada uno con su color y su
    // opacidad. El problema es que cada tramo lleva extremos redondeados,
    // así que en cada solape aparecía un círculo más oscuro: la víbora se
    // veía como un collar de cuentas en vez de un animal. Se notaba sobre
    // todo en el tablero claro.
    //
    // Con un único `Path2D` recorrido de la cola a la cabeza no hay solapes
    // que delatar, y el degradado de color se consigue con un gradiente
    // lineal entre los dos extremos.
    context.lineCap = 'round';
    context.lineJoin = 'round';

    const trazo = () => {
      context.beginPath();
      const cola = at(body.length - 1);
      context.moveTo(cola.x, cola.y);
      for (let i = body.length - 2; i >= 0; i--) {
        const p = at(i);
        context.lineTo(p.x, p.y);
      }
    };

    const grosor = cell * 0.74;

    // Resplandor por debajo: despega la figura del tablero sin recurrir a
    // un borde, que a este tamaño ensuciaría las curvas.
    context.save();
    context.shadowColor = glowColor;
    context.shadowBlur = cell * 0.9;
    context.strokeStyle = headColor;
    context.lineWidth = grosor;
    trazo();
    context.stroke();
    context.restore();

    const cola = at(body.length - 1);
    const cabeza = at(0);
    const cuerpoGrad = context.createLinearGradient(cola.x, cola.y, cabeza.x, cabeza.y);
    cuerpoGrad.addColorStop(0, tailColor);
    cuerpoGrad.addColorStop(1, headColor);
    context.strokeStyle = cuerpoGrad;
    context.lineWidth = grosor;
    trazo();
    context.stroke();

    // Lomo: una línea clara más fina por encima del mismo recorrido. Es lo
    // que convierte una cinta plana en un cilindro.
    context.strokeStyle = sheenColor;
    context.lineWidth = grosor * 0.35;
    trazo();
    context.stroke();

    // ── Cabeza ───────────────────────────────────────────────────
    const h = at(0);
    const headRadius = cell * 0.5;
    const cabezaGrad = context.createRadialGradient(
      h.x - headRadius * 0.3,
      h.y - headRadius * 0.35,
      headRadius * 0.15,
      h.x,
      h.y,
      headRadius * 1.1,
    );
    cabezaGrad.addColorStop(0, headLight);
    cabezaGrad.addColorStop(0.55, headColor);
    cabezaGrad.addColorStop(1, tailColor);
    context.fillStyle = cabezaGrad;
    context.beginPath();
    context.arc(h.x, h.y, headRadius, 0, Math.PI * 2);
    context.fill();

    // Ojos. Es el detalle que convierte una figura azul en un animal, y de
    // paso dice hacia dónde va antes de que se mueva.
    const v = VECTORS[direction.current] ?? VECTORS.right;
    const forward = headRadius * 0.38;
    const side = headRadius * 0.42;
    const eyeRadius = headRadius * 0.21;
    for (const sign of [-1, 1]) {
      const ex = h.x + v.x * forward - v.y * side * sign;
      const ey = h.y + v.y * forward + v.x * side * sign;
      context.fillStyle = eyeColor;
      context.beginPath();
      context.arc(ex, ey, eyeRadius, 0, Math.PI * 2);
      context.fill();
      context.fillStyle = '#06070a';
      context.beginPath();
      context.arc(
        ex + v.x * eyeRadius * 0.3,
        ey + v.y * eyeRadius * 0.3,
        eyeRadius * 0.52,
        0,
        Math.PI * 2,
      );
      context.fill();
      context.fillStyle = 'rgba(255,255,255,0.9)';
      context.beginPath();
      context.arc(ex - eyeRadius * 0.25, ey - eyeRadius * 0.3, eyeRadius * 0.2, 0, Math.PI * 2);
      context.fill();
    }
  }, []);

  const tick = useCallback(() => {
    direction.current = queued.current;
    const vector = VECTORS[direction.current];
    const head = snake.current[0];
    const next = { x: head.x + vector.x, y: head.y + vector.y };

    const hitWall = next.x < 0 || next.y < 0 || next.x >= GRID || next.y >= GRID;
    const hitSelf = snake.current.some((part) => part.x === next.x && part.y === next.y);
    if (hitWall || hitSelf) {
      setPhase('over');
      return;
    }

    // Copia de la posición actual ANTES de moverse: es el origen desde el que
    // interpola el dibujado hasta el siguiente paso.
    prevSnake.current = snake.current.map((part) => ({ ...part }));

    snake.current.unshift(next);

    if (next.x === food.current.x && next.y === food.current.y) {
      scoreRef.current += 10;
      setScore(scoreRef.current);
      eaten.current = { x: food.current.x, y: food.current.y, at: performance.now() };
      placeFood();
    } else {
      snake.current.pop();
    }
  }, [placeFood]);

  /* ── Tamaño del canvas ──────────────────────────────────────── */
  useEffect(() => {
    setupCanvas();
    draw();
    const wrap = canvasRef.current?.parentElement;
    if (!wrap || typeof ResizeObserver === 'undefined') return;
    // Girar el teléfono o cambiar el tamaño de la ventana cambia el tamaño en
    // pantalla; el búfer tiene que seguirlo o vuelve el estirado.
    const observer = new ResizeObserver(() => {
      setupCanvas();
      draw();
    });
    observer.observe(wrap);
    return () => observer.disconnect();
  }, [setupCanvas, draw]);

  /* ── Paleta ─────────────────────────────────────────────────── */
  // Si alguien cambia el tema del sistema con la partida empezada, los
  // colores leídos al arrancar se quedarían obsoletos y la víbora seguiría
  // pintada para el tema anterior.
  useEffect(() => {
    readPalette();
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => readPalette();
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, [readPalette]);

  /* ── Bucle de juego ─────────────────────────────────────────── */
  useEffect(() => {
    if (phase !== 'playing') return;

    let frame = 0;
    let last = performance.now();
    let accumulator = 0;

    const loop = (now: number) => {
      accumulator += now - last;
      last = now;
      // Acumulador: si el navegador se salta fotogramas (pestaña en segundo
      // plano, GC), el juego recupera el tiempo perdido en vez de ralentizarse.
      // El intervalo se relee en cada vuelta: si la víbora acaba de comer,
      // el paso siguiente ya es más rápido.
      let step = tickInterval(snake.current.length);
      while (accumulator >= step) {
        accumulator -= step;
        tick();
        step = tickInterval(snake.current.length);
      }
      // El dibujado va a la frecuencia de la pantalla y la lógica a pasos
      // fijos. Lo que se pinta es el estado del juego interpolado por la
      // fracción de paso ya transcurrida.
      draw(Math.min(1, accumulator / step));
      frame = requestAnimationFrame(loop);
    };

    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, [phase, tick, draw]);

  /* ── Teclado ────────────────────────────────────────────────── */
  useEffect(() => {
    const KEYS: Record<string, string> = {
      ArrowUp: 'up',
      ArrowDown: 'down',
      ArrowLeft: 'left',
      ArrowRight: 'right',
      w: 'up',
      s: 'down',
      a: 'left',
      d: 'right',
    };

    const onKeyDown = (event: KeyboardEvent) => {
      const next = KEYS[event.key];
      if (!next) return;
      // Solo se secuestra la tecla si el juego la usa: si no, se rompería el
      // desplazamiento normal de la página con las flechas.
      event.preventDefault();
      if (OPPOSITE[next] !== direction.current) queued.current = next;
    };

    if (phase === 'playing') window.addEventListener('keydown', onKeyDown, { passive: false });
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [phase]);

  /* ── Gestos táctiles ─────────────────────────────────────────
     En un teléfono no hay flechas: se juega deslizando el dedo sobre el
     tablero, en las cuatro direcciones.

     El giro se registra en `touchmove`, en cuanto el dedo recorre el
     umbral — NO al levantarlo. Es la diferencia entre un control que
     responde y uno que llega tarde: en Snake hace falta encadenar giros
     («derecha, abajo, derecha») más rápido de lo que se puede levantar y
     volver a apoyar el dedo. Tras cada giro el origen se recoloca, así que
     el mismo deslizamiento continuo puede encadenar varios sin soltar.

     El `touch-action: none` del canvas (ver islands.css) evita que el
     gesto arrastre la página en lugar de mover la serpiente. */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || phase !== 'playing') return;

    let originX = 0;
    let originY = 0;

    const onTouchStart = (event: TouchEvent) => {
      originX = event.touches[0].clientX;
      originY = event.touches[0].clientY;
    };

    const onTouchMove = (event: TouchEvent) => {
      const touch = event.touches[0];
      if (!touch) return;
      const deltaX = touch.clientX - originX;
      const deltaY = touch.clientY - originY;
      if (Math.abs(deltaX) < SWIPE_THRESHOLD && Math.abs(deltaY) < SWIPE_THRESHOLD) return;

      // El eje dominante decide: un gesto en diagonal se interpreta como el
      // movimiento que más recorrió, no como ninguno.
      const next =
        Math.abs(deltaX) > Math.abs(deltaY)
          ? deltaX > 0
            ? 'right'
            : 'left'
          : deltaY > 0
            ? 'down'
            : 'up';

      if (OPPOSITE[next] !== direction.current) queued.current = next;

      // Nuevo punto de partida: el siguiente giro se mide desde aquí.
      originX = touch.clientX;
      originY = touch.clientY;
    };

    canvas.addEventListener('touchstart', onTouchStart, { passive: true });
    canvas.addEventListener('touchmove', onTouchMove, { passive: true });
    return () => {
      canvas.removeEventListener('touchstart', onTouchStart);
      canvas.removeEventListener('touchmove', onTouchMove);
    };
  }, [phase]);

  async function start() {
    const { data } = await startGameSession(slug);
    tokenRef.current = data?.token ?? null;

    snake.current = Array.from({ length: INITIAL_LENGTH }, (_, i) => ({ x: 10 - i, y: 10 }));
    prevSnake.current = snake.current.map((part) => ({ ...part }));
    eaten.current = null;
    setupCanvas();
    readPalette();
    direction.current = 'right';
    queued.current = 'right';
    scoreRef.current = 0;
    setScore(0);
    setRank(null);
    placeFood();
    startedAt.current = Date.now();
    setPhase('playing');
    draw();
  }

  async function save() {
    if (!tokenRef.current) return;
    setPhase('saving');
    const { data } = await submitScore(slug, {
      token: tokenRef.current,
      nickname,
      score: scoreRef.current,
      duration_ms: Date.now() - startedAt.current,
    });
    setRank(data?.rank ?? null);
    setPhase('saved');
    // Avisa al ranking, que es una isla independiente, de que hay dato nuevo.
    window.dispatchEvent(new CustomEvent('score:saved', { detail: { slug } }));
  }

  return (
    <div className="game-panel snake">
      <div className="snake-hud">
        <span className="snake-score">
          {dict.games.score}: <strong>{score}</strong>
        </span>
        {rank !== null && (
          <span className="snake-rank">
            {dict.games.rank} #{rank}
          </span>
        )}
      </div>

      <div className="canvas-wrap">
        <canvas ref={canvasRef} width={480} height={480} aria-label="Snake" role="img" />

        {phase !== 'playing' && (
          <div className={`canvas-overlay ${phase === 'idle' ? 'canvas-overlay-idle' : ''}`}>
            {phase === 'over' || phase === 'saving' || phase === 'saved' ? (
              <>
                <p className="overlay-title">{dict.games.snake.gameOver}</p>
                <p className="overlay-score">{score}</p>
                {phase !== 'saved' && (
                  <>
                    <input
                      type="text"
                      maxLength={16}
                      value={nickname}
                      onChange={(event) => setNickname(event.target.value)}
                      placeholder={dict.games.yourName}
                      className="overlay-input"
                    />
                    <button
                      type="button"
                      className="submit"
                      disabled={phase === 'saving'}
                      onClick={() => void save()}
                    >
                      {phase === 'saving' ? dict.games.saving : dict.games.submit}
                    </button>
                  </>
                )}
                <button type="button" className="chip" onClick={() => void start()}>
                  {dict.games.playAgain}
                </button>
              </>
            ) : (
              <>
                <p className="overlay-hint">{dict.games.snake.instructions}</p>
                <button type="button" className="submit" onClick={() => void start()}>
                  {dict.games.play}
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
