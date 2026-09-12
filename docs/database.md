# Base de datos — SQLite (modo WAL)

> Estado: **diseño aprobado** · Última actualización: 2026-09-10

---

## 1. Por qué SQLite

Volumen esperado: decenas de posts, unidades de proyectos, miles de puntuaciones. La escritura es
esporádica (el admin publica; los visitantes leen). En ese perfil, SQLite en modo WAL es **más rápido
que Postgres** porque elimina la latencia de red y el proceso servidor — y en 512 MB de RAM, ese proceso
servidor cuesta ~120 MB que no tenemos.

Configuración obligatoria en el arranque de Django:

```
PRAGMA journal_mode = WAL;      -- lecturas concurrentes durante escrituras
PRAGMA synchronous = NORMAL;    -- durabilidad suficiente, muchas menos llamadas fsync
PRAGMA busy_timeout = 5000;     -- espera en vez de lanzar "database is locked"
PRAGMA foreign_keys = ON;       -- Django no lo activa por defecto
```

**Persistencia:** volumen Docker `api_data` montado en `/data`. La base vive en `/data/db.sqlite3`,
nunca dentro de la imagen. Un `docker compose down` no debe poder borrar el contenido del sitio.

**Respaldo:** `sqlite3 db.sqlite3 ".backup /data/backups/db-$(date +%F).sqlite3"` por cron diario,
reteniendo 7 días. `.backup` es seguro con la base en uso; copiar el archivo con `cp` no lo es.

---

## 2. Convenciones

- Todo modelo hereda de `TimeStampedModel` (`created_at`, `updated_at`).
- Los campos traducibles se duplican con sufijo `_es` / `_en`. El español es obligatorio; el inglés
  puede quedar vacío y cae al español (degradación elegante, nunca una página en blanco).
- El Markdown se guarda **dos veces**: la fuente (`body_md_*`) y el HTML ya renderizado (`body_html_*`),
  regenerado en `save()`. Renderizar Markdown en cada petición es trabajo repetido y desperdiciado.
- `slug` es único y estable: es una URL pública y romperla rompe enlaces entrantes.
- Nunca se almacena una IP en claro. Solo `ip_hash = sha256(ip + SECRET_SALT)`.

---

## 3. Módulo `site` — identidad y CV vivo

### `Profile` (singleton)
| Campo | Tipo | Notas |
|---|---|---|
| `full_name` | Char(120) | "Pedro Mamani Tito" |
| `role_es` / `role_en` | Char(160) | "Desarrollo de Software · Mobile · Backend" |
| `headline_es` / `headline_en` | Char(255) | titular del hero |
| `bio_es` / `bio_en` | Text | Markdown |
| `bio_html_es` / `bio_html_en` | Text | renderizado en `save()` |
| `email` | Email | |
| `phone` | Char(32) | |
| `location_es` / `location_en` | Char(120) | "El Alto — La Paz, Bolivia" |
| `availability_es` / `availability_en` | Char(255) | "Incorporación inmediata" |
| `cv_es` / `cv_en` | File | PDF descargable |
| `avatar` | Image | |

### `SocialLink`
`name` · `url` · `icon` (identificador de icono) · `order`

### `SkillGroup` / `Skill`
`SkillGroup`: `name_es` / `name_en` · `order` — "Mobile", "Backend", "Bases de datos", "Herramientas"
`Skill`: `group` (FK) · `name` · `level` (1–5) · `is_primary` (bool) · `order`

### `ExperienceItem`
`role_es`/`role_en` · `organization` · `start_date` · `end_date` (nulo = actual) ·
`description_es`/`description_en` · `highlights_es`/`highlights_en` (Text, una línea por logro) · `order`

> Estos modelos son la fuente de verdad del apartado "Sobre mí" **y del CV en PDF**. Una sola edición,
> dos salidas. Ese es el punto.

---

## 4. Módulo `projects`

### `Technology`
| Campo | Tipo | Notas |
|---|---|---|
| `name` | Char(60) unique | "Kotlin", "Docker" |
| `slug` | Slug unique | usado en el filtro de la URL |
| `category` | Char(choices) | `mobile` · `backend` · `frontend` · `devops` · `design` |
| `color` | Char(7) | hex, para el badge |
| `icon` | Char(60) | identificador del icono |
| `order` | Int | |

### `Project`
| Campo | Tipo | Notas |
|---|---|---|
| `slug` | Slug unique | |
| `title_es` / `title_en` | Char(160) | |
| `tagline_es` / `tagline_en` | Char(255) | una línea para la tarjeta |
| `summary_es` / `summary_en` | Text | 2–3 frases |
| `body_md_es` / `body_md_en` | Text | caso de estudio completo |
| `body_html_es` / `body_html_en` | Text | renderizado |
| `role_es` / `role_en` | Char(160) | "Desarrollo completo a cargo" |
| `cover` | Image | |
| `year` | Int | |
| `status` | Char(choices) | `draft` · `published` |
| `featured` | Bool | aparece en la home |
| `repo_url`, `live_url`, `store_url`, `video_url` | URL, opcionales | |
| `technologies` | M2M → `Technology` | |
| `order` | Int | |

Índices: `(status, featured, -year)`, `slug`.

### `ProjectImage`
`project` (FK) · `image` · `caption_es`/`caption_en` · `order`

### `ProjectMetric`
`project` (FK) · `label_es`/`label_en` · `value` (Char) · `order`
Para datos duros: *"Publicada en Google Play"*, *"3 formatos de exportación"*. Los números concretos
convencen más que los adjetivos.

**Semilla inicial:** MentePro (2025) · ManiPDF (2026) · ManiFarm (2026), tomados del CV.

---

## 5. Módulo `blog`

### `Category`
`slug` unique · `name_es`/`name_en` · `description_es`/`description_en` · `order`

### `Tag`
`slug` unique · `name_es`/`name_en`

### `Post`
| Campo | Tipo | Notas |
|---|---|---|
| `slug` | Slug unique | |
| `title_es` / `title_en` | Char(200) | |
| `excerpt_es` / `excerpt_en` | Text(500) | también se usa como meta description |
| `body_md_es` / `body_md_en` | Text | Markdown, editado en el Admin |
| `body_html_es` / `body_html_en` | Text | renderizado en `save()` |
| `cover` | Image | |
| `category` | FK → `Category` | |
| `tags` | M2M → `Tag` | |
| `status` | Char(choices) | `draft` · `published` |
| `published_at` | DateTime | |
| `reading_minutes_es` / `_en` | Int | calculado en `save()` |
| `views` | Int | incremento con `F()`, sin condición de carrera |

Índices: `(status, -published_at)`, `slug`, `category`.

**Búsqueda:** en el MVP, `icontains` sobre título + extracto + cuerpo. Con menos de ~200 posts la respuesta
es instantánea y no añade dependencias. La migración a **FTS5** queda planificada para la fase de
optimización, cuando exista volumen que la justifique.

---

## 6. Módulo `games`

### `Game`
`slug` unique · `name_es`/`name_en` · `description_es`/`description_en` · `icon` · `enabled` · `order` ·
`max_plausible_score` (Int, para validación en servidor)

### `QuizQuestion` / `QuizOption`
`QuizQuestion`: `game` (FK) · `text_es`/`text_en` · `explanation_es`/`explanation_en` · `difficulty` (1–3) · `enabled`
`QuizOption`: `question` (FK) · `text_es`/`text_en` · `is_correct` (Bool)

> El quiz reutiliza el mismo modelo bilingüe del resto del sitio: las preguntas se cargan y traducen
> desde el Admin, sin tocar código.

### `Score`
| Campo | Tipo | Notas |
|---|---|---|
| `game` | FK → `Game` | |
| `nickname` | Char(16) | saneado, sin HTML, con filtro de palabras |
| `score` | Int | |
| `duration_ms` | Int | usado para detectar puntuaciones imposibles |
| `meta` | JSON | detalle por juego |
| `ip_hash` | Char(64) | anti-abuso, nunca la IP real |
| `created_at` | DateTime | |

Índice: `(game, -score, created_at)` — es exactamente la consulta del ranking.

**Anti-trampa (defensa en profundidad, no perfección):**
1. `POST /games/{slug}/session/` devuelve un token firmado con HMAC que incluye la marca de tiempo.
2. El envío de puntuación exige ese token, con validez de 30 minutos y un solo uso.
3. El servidor rechaza `score > max_plausible_score` y combinaciones score/duración imposibles.
4. Límite de 20 envíos por hora por `ip_hash`.

No es infalible — nada que corra en el navegador lo es — pero convierte el fraude casual en trabajo.

---

## 7. Módulo `contact`

### `ContactMessage`
`name` · `email` · `subject` · `message` · `locale` (es/en) · `ip_hash` · `user_agent` ·
`status` (`new` · `read` · `replied` · `spam`) · `created_at`

El mensaje se **persiste antes** de intentar el aviso. Si el canal falla, el mensaje no se pierde:
queda en el Admin. Perder un contacto de un reclutador por un fallo de red no es aceptable.
`delivered` en False marca justamente eso: guardado, pero sin avisar.

---

## 8. Módulo `metrics`

### `MetricSnapshot`
`cpu_percent` · `mem_used_mb` · `mem_total_mb` · `disk_used_gb` · `disk_total_gb` ·
`load_1m` · `uptime_seconds` · `created_at` (indexado)

Escrito por un comando de gestión ejecutado por cron cada 5 minutos, que además purga todo lo anterior
a 24 horas. Techo duro: **288 filas**. La tabla no puede crecer sin control.

---

## 9. Diagrama de relaciones

```
Profile (1) ──< SocialLink
             ──< SkillGroup ──< Skill
             ──< ExperienceItem

Technology >──< Project ──< ProjectImage
                        ──< ProjectMetric

Category (1) ──< Post >──< Tag

Game (1) ──< Score
         ──< QuizQuestion ──< QuizOption

ContactMessage   (independiente)
MetricSnapshot   (independiente, serie temporal)
```
