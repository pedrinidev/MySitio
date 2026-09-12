# Contrato de la API — v1

> Estado: **diseño aprobado** · Última actualización: 2026-09-10
> Base: `https://pedrinidev.com/api/v1/`

---

## Convenciones generales

- **Idioma:** todo endpoint de lectura acepta `?lang=es|en` (por defecto `es`). La respuesta llega con los
  campos ya aplanados: `title`, nunca `title_es`.
- **Autenticación:** ninguna. Toda la lectura es pública; toda la escritura está limitada por throttling.
- **Paginación:** `?page=` y `?page_size=` (máximo 50). Formato:
  `{ "count": 42, "next": "...", "previous": null, "results": [...] }`
- **Errores:** siempre un objeto, nunca texto plano.
  ```json
  { "detail": "Mensaje legible", "code": "throttled", "errors": { "email": ["Formato inválido"] } }
  ```
- **Códigos:** `200` · `201` · `400` validación · `404` · `429` límite excedido · `503` dependencia caída.

---

## `site`

### `GET /profile/?lang=es`
Perfil, enlaces sociales, grupos de habilidades y experiencia, en una sola respuesta (el frontend lo pide
una vez en el build, no vale la pena fragmentarlo).

```json
{
  "full_name": "Pedro Mamani Tito",
  "role": "Desarrollo de Software · Mobile · Backend",
  "headline": "...",
  "bio_html": "<p>...</p>",
  "location": "El Alto — La Paz, Bolivia",
  "availability": "Incorporación inmediata",
  "cv_url": "/media/cv/CV_PMT-2026.pdf",
  "socials":    [{ "name": "GitHub", "url": "...", "icon": "github" }],
  "skill_groups": [{ "name": "Mobile", "skills": [{ "name": "Kotlin", "level": 5 }] }],
  "experience":  [{ "role": "...", "organization": "...", "start_date": "2024-10-01", "end_date": "2024-11-30", "highlights": ["..."] }]
}
```

---

## `projects`

| Método | Ruta | Notas |
|---|---|---|
| `GET` | `/technologies/?lang=` | catálogo para el filtro |
| `GET` | `/projects/?lang=&tech=&featured=&year=` | listado; `tech` acepta varios slugs separados por coma |
| `GET` | `/projects/{slug}/?lang=` | detalle con `body_html`, galería y métricas |

Listado — cada elemento: `slug`, `title`, `tagline`, `summary`, `cover_url`, `year`, `featured`,
`technologies[]`, `links{}`.
Detalle — añade `body_html`, `role`, `images[]`, `metrics[]`.

---

## `blog`

| Método | Ruta | Notas |
|---|---|---|
| `GET` | `/blog/categories/?lang=` | |
| `GET` | `/blog/tags/?lang=` | |
| `GET` | `/blog/posts/?lang=&category=&tag=&q=&page=` | `q` busca en título, extracto y cuerpo |
| `GET` | `/blog/posts/{slug}/?lang=` | incrementa `views` con `F()` |

Solo se exponen posts con `status=published` y `published_at <= ahora`. Los borradores no existen para la API.

---

## `games`

| Método | Ruta | Límite | Notas |
|---|---|---|---|
| `GET` | `/games/?lang=` | 60/min | juegos activos |
| `GET` | `/games/{slug}/questions/?lang=` | 60/min | solo quiz; **nunca** revela `is_correct` |
| `POST` | `/games/{slug}/session/` | 30/h | devuelve `{ "token": "...", "expires_in": 1800 }` |
| `POST` | `/games/{slug}/scores/` | 20/h | requiere token válido y de un solo uso |
| `GET` | `/games/{slug}/scores/?limit=10` | 60/min | ranking |

**Corrección del quiz en el servidor.** El cliente envía las respuestas elegidas; el servidor calcula la
puntuación. Enviar `is_correct` al navegador sería regalar las respuestas en el DevTools.

`POST /scores/` — cuerpo: `{ "token": "...", "nickname": "pedro", "answers": [...] }` o
`{ "token": "...", "nickname": "pedro", "score": 320, "duration_ms": 48000 }` según el juego.
Rechaza con `400` si el token expiró, ya se usó, o la puntuación es implausible.

---

## `contact`

### `POST /contact/` — límite: 3 por hora por IP hasheada

```json
{ "name": "...", "email": "...", "subject": "...", "message": "...",
  "locale": "es", "website": "", "elapsed_ms": 8400 }
```

- `website` es el **honeypot**: si viene con contenido, se responde `201` y se descarta en silencio.
  Un bot no debe saber que fue detectado.
- `elapsed_ms < 3000` se marca como `spam` pero también responde `201`.
- El mensaje se guarda **antes** de intentar el aviso (ver `core/notifications.py`).

---

## `metrics`

| Método | Ruta | Caché | Notas |
|---|---|---|---|
| `GET` | `/metrics/live/` | 10 s | estado actual del droplet |
| `GET` | `/metrics/history/?hours=24` | 60 s | serie temporal para el sparkline |

```json
{
  "cpu_percent": 4.2,
  "memory": { "used_mb": 372, "total_mb": 486, "percent": 76.5 },
  "disk":   { "used_gb": 3.1, "total_gb": 9.6, "percent": 32.3 },
  "load_1m": 0.08,
  "uptime_seconds": 1847293,
  "measured_at": "2026-09-10T14:32:11Z"
}
```

Se exponen porcentajes y agregados. **No** se expone la lista de procesos, ni rutas del sistema de
archivos, ni nombres de host: son datos de reconocimiento para un atacante y no aportan nada al visitante.

---

## Webhook interno

`repository_dispatch` de GitHub, disparado desde una señal `post_save` de Django al publicar contenido.
El token vive en variable de entorno del contenedor `api`, con permiso mínimo (solo `contents: write` en
este repositorio) y **jamás** en la base de datos ni en el código.
