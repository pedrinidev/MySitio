# Módulos y plan de construcción

> Estado: **diseño aprobado** · Última actualización: 2026-09-10

Regla del proyecto: **backend primero, luego frontend**. Ningún módulo se considera terminado hasta
cumplir la definición de completado (sección 4).

---

## 1. Mapa de módulos

| # | Módulo | Estado | Entregable observable |
|---|---|---|---|
| **M0** | Fundación | ✅ | `make init` levanta el entorno completo |
| **M1** | `site` (perfil / CV) | ✅ | Admin editable + `/profile/` · datos reales del CV |
| **M2** | `projects` | ✅ | Filtros por tecnología · MentePro, ManiPDF, ManiFarm |
| **M3** | `blog` | ✅ | Markdown → HTML saneado, búsqueda, bilingüe |
| **M4** | `games` | ✅ | Quiz corregido en servidor + Snake · anti-trampa con HMAC |
| **M5** | `contact` | ✅ | Honeypot + trampa temporal · persiste antes de enviar |
| **M6** | `metrics` | ✅ | CPU/RAM del **host** vía `/proc` montado · 0 consultas |
| **M7** | Base del frontend | ✅ | Sistema de diseño, i18n, cliente de API que falla ruidosamente |
| **M8** | Secciones y animaciones | ✅ | GSAP + ScrollTrigger · `prefers-reduced-motion` respetado |
| **M9** | Islas interactivas | ✅ | 6 islas · carga diferida por `client:visible` |
| **M10** | Infraestructura de producción | ✅ | Imágenes, Nginx+TLS, 3 workflows, script del droplet |
| **M11** | Optimización y cierre | ✅ | Sin N+1 · h1 en todas las páginas · 76 pruebas |

**Pendiente de Pedro** (no es código): crear el droplet, apuntar el DNS,
configurar el canal de avisos y cargar los secretos en GitHub. Ver `deployment.md`.

---

## 2. Detalle por módulo

### M0 — Fundación
Estructura del monorepo · `settings/` dividido (`base` / `dev` / `prod`) · app `core`
(`TimeStampedModel`, `TranslatedModelSerializer`, paginación, manejador de excepciones, utilidades de
hash de IP y render de Markdown) · `compose.dev.yml` con recarga automática · `ruff` + `black` + `pytest`
· esqueleto de `/docs`.

**Criterio de aceptación:** un desarrollador clona el repositorio, ejecuta un comando y tiene el Admin
funcionando. Sin pasos manuales no documentados.

### M1 — `site`
Modelos `Profile`, `SocialLink`, `SkillGroup`, `Skill`, `ExperienceItem` · Admin con `Profile` como
singleton real (bloquear la creación de un segundo registro) · endpoint `/profile/` · **datos semilla
cargados desde el CV** mediante un comando de gestión.

### M2 — `projects`
Modelos y Admin con `ProjectImage` / `ProjectMetric` en línea · filtro por `?tech=` · optimización con
`prefetch_related` sobre tecnologías (evitar N+1 desde el primer día, no después) · semilla con
MentePro, ManiPDF y ManiFarm.

### M3 — `blog`
Modelos · render de Markdown en `save()` con saneado del HTML resultante · cálculo de tiempo de lectura ·
búsqueda con `icontains` · paginación · filtros por categoría y tag.

> **Seguridad:** el Markdown del Admin se convierte en HTML que se inyecta en la página. Aunque el único
> autor sea el dueño del sitio, el resultado se sanea con `bleach` y una lista blanca de etiquetas.
> Una cuenta de admin comprometida no debe convertirse en XSS persistente.

### M4 — `games`
Modelos · servicio de token HMAC · validación de plausibilidad en servidor · endpoints de ranking y envío ·
throttling específico.

**Juegos propuestos para el MVP** (a confirmar):
1. **DevOps Quiz** *(bilingüe, preguntas desde el Admin)* — es el que mejor encaja con el sitio: reutiliza
   el modelo de contenido bilingüe y demuestra el CMS funcionando de verdad.
2. **Snake** *(canvas, estética Apple)* — el gancho visual, cero backend salvo la puntuación.

*Memory con logos de tecnologías* queda como tercero opcional para la fase de optimización.

### M5 — `contact`
Modelo · servicio que compone el aviso · entrega por canal intercambiable (`core/notifications.py`) ·
honeypot + trampa temporal +
límite por IP hasheada · **persistir antes de avisar** · el fallo del canal se registra en log pero devuelve
éxito al usuario (el mensaje ya está guardado).

### M6 — `metrics`
Servicio con `psutil` apuntando a `/host/proc` · caché de 10 s · endpoints `live` e `history` ·
comando de gestión `snapshot_metrics` con purga a 24 h.

### M7 — Base del frontend
Astro + Tailwind + integración de React · tokens de diseño (color, tipografía, espaciado, radios) ·
enrutado `[lang]` · cliente de API tipado que **falla el build si la API no responde** · `BaseLayout`
con SEO, Open Graph y `hreflang` · componentes de interfaz.

### M8 — Secciones y animaciones
Home con hero animado · grid de proyectos · listado y detalle del blog · presets de GSAP centralizados ·
soporte de `prefers-reduced-motion` · verificación de rendimiento en móvil real.

### M9 — Islas interactivas
`ProjectFilter` · `BlogSearch` con debounce · `GameSnake` · `GameQuiz` · `MetricsDashboard` con sparkline ·
`ContactForm` con validación en cliente reflejando exactamente la del servidor.

### M10 — Infraestructura de producción
`api.Dockerfile` multi-etapa sobre Alpine (etapa de compilación para `psutil`, etapa final sin toolchain) ·
`web.Dockerfile` (Node build → `nginx:alpine`) · `nginx.conf` con TLS, cabeceras y `limit_req` ·
`compose.prod.yml` · tres workflows de GitHub Actions · `droplet-setup.sh` · Certbot · UFW · fail2ban ·
swap de 2 GB · rotación de logs de Docker · `deployment.md`.

### M11 — Optimización y cierre
Auditoría Lighthouse · presupuesto de bundle · revisión de accesibilidad (contraste, foco, navegación por
teclado, `aria`) · consultas N+1 · revalidación del consumo real de RAM en el droplet · evaluación de
FTS5 y Three.js · documentación al día.

---

## 3. Orden de ejecución

```
M0
 └─ M1 ─┬─ M2 ─┐
        ├─ M3 ─┤
        ├─ M4 ─┤          M6 (independiente, en paralelo)
        └─ M5 ─┘
               └────── M7 ── M8 ── M9 ── M10 ── M11
```

`M6` no depende de `M1` y puede construirse en cualquier momento. Todo lo demás es secuencial.

---

## 4. Definición de completado

Un módulo está terminado únicamente cuando cumple **las seis condiciones**:

1. Funciona sin errores en el entorno de desarrollo.
2. Está integrado con el resto del sistema (no es una pieza suelta).
3. Maneja errores explícitamente: entrada inválida, dependencia caída, caso vacío.
4. Valida toda entrada del usuario en el servidor, no solo en el cliente.
5. Está documentado en `/docs` **en el mismo commit** que lo implementa.
6. Fue revisado contra las reglas de calidad: nombres descriptivos, sin duplicación, sin lógica en las vistas.

Un módulo que "funciona pero no está documentado" no está terminado.
