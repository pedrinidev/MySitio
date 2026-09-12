# Arquitectura — pedrinidev.com

> Portafolio interactivo de Pedro Mamani Tito.
> Estado: **diseño aprobado** · Última actualización: 2026-09-10

---

## 1. Objetivo del sistema

Un portafolio personal que funcione simultáneamente como:

1. **Vitrina de producto** — MentePro, ManiPDF y ManiFarm presentados con nivel de detalle profesional.
2. **Prueba de competencia en infraestructura** — el propio sitio está contenerizado, desplegado por CI/CD, servido con HTTPS y monitoreado en vivo. No se afirma; se demuestra.
3. **CV vivo y bilingüe** — el contenido de "sobre mí" sale de la misma base de datos que alimenta el CV en PDF.

**Narrativa elegida:** *desarrollador de software que opera su propia infraestructura*. Los proyectos son el héroe; la infraestructura es la evidencia.

---

## 2. Restricción que define todo el diseño

El destino es un **Droplet de DigitalOcean de $4/mes: 512 MB de RAM, 1 vCPU, 10 GB de disco**.

Presupuesto de memoria en régimen permanente:

| Componente              | Estimado | **Medido** |
|-------------------------|----------|------------|
| Ubuntu 24.04 minimal    | ~130 MB  | — *(estimado)* |
| Docker daemon           | ~70 MB   | — *(estimado)* |
| Gunicorn + Django (2 workers, 4 hilos) | ~150 MB | **104 MB** |
| Nginx (alpine)          | ~15 MB   | **3,6 MB** |
| **Total**               | ~365 MB  | **~308 MB** |
| Margen sobre 512 MB     | ~145 MB  | **~204 MB** |

> Las dos cifras marcadas como medidas salen de `docker stats` sobre la pila
> de producción real (imágenes finales, `compose.prod.yml`, contenido cargado).
> Las dos primeras filas siguen siendo estimaciones: dependen del droplet y no
> se pueden medir hasta tenerlo.
>
> El margen real es **más holgado** de lo previsto: Gunicorn con `gthread`
> consume bastante menos que dos workers sincrónicos, y Nginx sirviendo
> archivos estáticos es casi gratis. Aun así, las tres reglas de abajo siguen
> vigentes: el margen sirve para absorber picos, no para gastarlo.

Los contenedores llevan además un **tope duro de memoria** (`api` 260 MB,
`web` 64 MB). Si Django se desmadra, el OOM killer se lo lleva a él y no a
Nginx: un sitio que sirve HTML sin API es mucho mejor que un servidor caído.

Tres consecuencias no negociables:

1. **El droplet nunca compila.** Un build de Astro/Vite pide 400–800 MB de pico. En 512 MB significa thrashing de swap o un OOM kill. Todo build ocurre en GitHub Actions.
2. **No hay Redis, ni Celery, ni Postgres.** Caché en memoria del proceso (`LocMemCache`), tareas por `cron` del host, SQLite en modo WAL.
3. **No hay proceso Node en producción.** Astro se compila a HTML estático; Nginx lo sirve desde disco.

---

## 3. Vista de alto nivel

```
                        Internet
                           │
                           ▼
                 ┌──────────────────┐
                 │  Nginx (alpine)  │  :80 → :443
                 │  reverse proxy   │  TLS (Certbot), HTTP/2,
                 │  + static server │  gzip, headers, rate limit
                 └────────┬─────────┘
                          │
        ┌─────────────────┼──────────────────────┐
        │                 │                      │
        ▼                 ▼                      ▼
   /srv/web           /api/  /admin/        /media/
   dist/ de Astro     proxy_pass            volumen ro
   (HTML plano)            │
                           ▼
                 ┌──────────────────┐
                 │ Gunicorn (gthread)│
                 │ Django + DRF      │
                 └────────┬──────────┘
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
       SQLite (WAL)              /host/proc, /host/sys
       volumen api_data          montados ro → psutil
```

**Dos contenedores en régimen permanente:** `web` (Nginx) y `api` (Gunicorn). Un tercero, `certbot`, corre bajo demanda con un perfil de Compose.

---

## 4. Modelo de renderizado: estático + islas

### 4.1 Qué se prerenderiza (build time, en GitHub Actions)

Astro consulta la API pública de Django **durante el build en CI** y genera HTML plano para:

- Home (`/es/`, `/en/`)
- Cada proyecto (`/es/proyectos/[slug]`, `/en/projects/[slug]`)
- Cada post del blog, en ambos idiomas
- Listados, categorías, tags, sobre mí, contacto

Resultado: el visitante recibe HTML ya renderizado. Google indexa todo. **Si Django se cae, el sitio sigue en pie** — solo dejan de responder las partes vivas.

### 4.2 Qué se hidrata en el cliente (islas React)

| Isla                | Directiva        | Consume |
|---------------------|------------------|---------|
| `ProjectFilter`     | `client:load`    | datos ya embebidos en el HTML |
| `BlogSearch`        | `client:idle`    | `GET /api/v1/blog/posts/?q=` |
| `MetricsDashboard`  | `client:visible` | `GET /api/v1/metrics/live` + `/history` |
| `GameSnake`, `GameQuiz` | `client:visible` | `POST /scores`, `GET /scores` |
| `ContactForm`       | `client:visible` | `POST /api/v1/contact/` |

El selector de idioma es HTML puro: son dos URLs distintas, no necesita JavaScript.

### 4.3 Cómo se actualiza el contenido

```
Admin de Django  →  señal post_save  →  POST a GitHub API
                                        (repository_dispatch)
                                              │
                                              ▼
                                     Workflow content-rebuild
                                     rebuild de Astro (~2 min)
                                              │
                                              ▼
                                     push a GHCR → droplet pull
```

Publicar un post cuesta ~2 minutos hasta estar visible. A cambio: cero RAM extra, SEO perfecto y resiliencia total.

> ⚠️ **Dependencia de arranque:** el build de Astro en CI necesita que la API de producción esté accesible. En el primer despliegue hay que levantar `api` **antes** de construir `web`. El cliente de API debe **fallar ruidosamente** si no obtiene datos — un build exitoso con contenido vacío es peor que un build roto.

---

## 5. Capas del backend (Django)

Separación estricta, según regla 3 del proyecto: **los controladores no contienen lógica de negocio**.

```
Vista (DRF)      → valida entrada, delega, serializa salida.  Sin reglas de negocio.
Servicio         → toda la lógica: cálculos, envío de correo, validación de scores.
Selector/Manager → consultas complejas y optimizadas al ORM.
Modelo           → estructura, restricciones e invariantes de datos.
```

Estructura de cada módulo:

```
modules/<nombre>/
├── models.py        # datos e invariantes
├── managers.py      # querysets reutilizables
├── services.py      # lógica de negocio (funciones puras cuando se pueda)
├── serializers.py   # contrato de entrada/salida
├── views.py         # delgadas: entrada → servicio → salida
├── urls.py
├── admin.py         # experiencia de edición
└── tests/
```

Regla de oro: **si una vista tiene un `if` que no es sobre validación o permisos, esa lógica pertenece a `services.py`.**

---

## 6. Estrategia bilingüe

**Decisión: campos por idioma en el modelo** (`title_es` / `title_en`).

El aplanado ocurre en una única pieza reutilizable, `core/serializers.TranslatedModelSerializer`:

```
Base de datos:   title_es = "Despliegue continuo"
                 title_en = "Continuous deployment"

Petición:        GET /api/v1/blog/posts/?lang=en

Respuesta JSON:  { "title": "Continuous deployment", ... }
```

El frontend nunca ve sufijos de idioma. Cambiar de idioma es cambiar un parámetro.

- **Cadenas de interfaz** (botones, etiquetas, navegación) → archivos JSON en Astro, no en la base de datos. No tiene sentido pagar una consulta por la palabra "Enviar".
- **Contenido** (proyectos, posts, biografía, preguntas del quiz) → Django Admin.
- **URLs** → prefijo de ruta (`/es/`, `/en/`) por SEO. `/` redirige a `/es/` mediante meta refresh estático.
- **Extensión futura a aymara:** requiere migración de columnas nuevas. Documentado como costo aceptado en `decisions.md`.

---

## 7. Métricas del servidor desde dentro de un contenedor

El problema: `psutil` dentro de un contenedor mide el contenedor, no el host.

La solución: montar los sistemas de archivos virtuales del host en modo lectura y redirigir `psutil`.

```yaml
volumes:
  - /proc:/host/proc:ro
  - /sys:/host/sys:ro
  - /:/host/root:ro
```

```python
psutil.PROCFS_PATH = "/host/proc"   # CPU, memoria, uptime, load average
psutil.disk_usage("/host/root")     # disco real del droplet
```

- Los valores se cachean **10 segundos** en `LocMemCache`: 100 visitantes concurrentes generan 6 lecturas por minuto, no 6000.
- Un comando de gestión ejecutado por `cron` cada 5 minutos guarda un `MetricSnapshot` y purga lo anterior a 24 h → 288 filas máximo, suficiente para el sparkline del dashboard.

> ⚠️ **Nota de seguridad:** montar `/proc` en modo lectura expone la lista de procesos del host al contenedor. En un droplet de un solo inquilino es aceptable; en infraestructura compartida no lo sería. Queda registrado como riesgo asumido conscientemente.

---

## 8. Frontend (Astro + React Islands)

```
apps/web/src/
├── components/
│   ├── ui/          # Button, Card, Badge, Container, Prose  (.astro)
│   ├── sections/    # Hero, ProjectGrid, Timeline, CTA       (.astro)
│   └── islands/     # ProjectFilter, BlogSearch, Games,      (.tsx)
│                    # MetricsDashboard, ContactForm
├── layouts/         # BaseLayout, PostLayout, ProjectLayout
├── pages/
│   ├── [lang]/index.astro
│   ├── [lang]/proyectos/[slug].astro
│   ├── [lang]/blog/[slug].astro
│   ├── [lang]/juegos/[slug].astro
│   └── index.astro          # redirección estática a /es/
├── lib/
│   ├── api.ts               # cliente tipado, falla ruidosamente
│   ├── i18n/{es,en}.json    # cadenas de interfaz
│   └── motion/              # presets de GSAP reutilizables
└── styles/tokens.css        # sistema de diseño
```

### Lenguaje visual (estilo Apple)

- Tipografía grande, jerarquía marcada, espacio en blanco generoso.
- Movimiento **al servicio del contenido**: revelados con máscara, parallax sutil, secciones ancladas con `scrub`, contadores animados.
- Presets de GSAP centralizados en `lib/motion/` — nada de animaciones ad-hoc dispersas.
- **`prefers-reduced-motion` es obligatorio**, no opcional: si el visitante lo pide, todo aparece sin transición.
- Objetivo de rendimiento: **LCP < 1.5 s, CLS < 0.05**, ≤ 120 KB de JS comprimido en la home.

**Three.js queda fuera del MVP.** Añade ~150 KB comprimidos y compite directamente con el objetivo de LCP. Se reevalúa en la fase de optimización, y solo con carga diferida y bajo demanda.

---

## 9. Seguridad

| Capa       | Medida |
|------------|--------|
| Django     | `DEBUG=False`, `SECRET_KEY` por entorno, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` |
| Transporte | HTTPS forzado, HSTS con preload, `SECURE_PROXY_SSL_HEADER`, cookies `Secure` + `HttpOnly` |
| Cabeceras  | CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` |
| CORS       | Lista blanca estricta: solo `https://pedrinidev.com` |
| API        | Throttling de DRF: anónimo 60/min · contacto 3/h · scores 20/h. Lecturas en caché de proceso, escrituras en caché compartida (ADR-014) |
| Build      | `X-Build-Token` exime al prerenderizado del límite; comparación en tiempo constante (ADR-013) |
| Admin      | Ruta no adivinable, `limit_req` en Nginx, sin acceso desde la API pública |
| Formulario | Honeypot + trampa temporal (envío en < 3 s = bot) + límite por IP hasheada |
| Juegos     | Token de sesión firmado con HMAC + validación de plausibilidad en servidor |
| Privacidad | **Nunca se guardan IPs en claro** — solo `sha256(ip + SALT)` |
| Servidor   | UFW (22/80/443), fail2ban, SSH solo por clave, actualizaciones automáticas |

---

## 10. Rendimiento

- **Gunicorn:** `--worker-class gthread --workers 2 --threads 4 --max-requests 500 --max-requests-jitter 50`. `gthread` porque la carga es de E/S, no de CPU; `max-requests` recicla workers y neutraliza fugas de memoria lentas.
- **SQLite:** `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`. WAL permite lecturas concurrentes durante una escritura.
- **Nginx:** `gzip` activo, `immutable` + 1 año de caché para assets con hash, `no-cache` para HTML.
- **WhiteNoise** sirve los estáticos del admin de Django — evita coordinar `collectstatic` con un volumen de Nginx para cuatro archivos CSS.
- **Rotación de logs de Docker obligatoria** (`max-size: 10m`, `max-file: 3`). Sin esto, los logs llenan los 10 GB de disco en semanas. Es la causa más común de caída en droplets pequeños.

---

## 11. Estructura del repositorio (monorepo)

```
MySite/
├── .github/workflows/     ci.yml · deploy.yml · content-rebuild.yml
├── apps/
│   ├── api/               Django + DRF
│   └── web/               Astro
├── infra/
│   ├── docker/            api.Dockerfile · web.Dockerfile
│   ├── nginx/             nginx.conf · site.conf
│   ├── compose.dev.yml
│   ├── compose.prod.yml
│   └── scripts/           droplet-setup.sh · deploy.sh · backup.sh
├── docs/
└── README.md
```

Monorepo por una razón concreta: el contrato entre la API y el frontend cambia en un solo commit y un solo PR. En dos repositorios, ese contrato se rompe en silencio.
