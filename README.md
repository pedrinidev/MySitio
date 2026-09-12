# pedrinidev.com

Portafolio personal de **Pedro Mamani Tito** — desarrollador de software
(mobile · backend) que opera su propia infraestructura.

El sitio no solo *cuenta* que sé desplegar: **es la prueba**. Está
contenerizado, se despliega solo con GitHub Actions y corre en un droplet de
4 USD al mes cuyas métricas reales podés ver en vivo en la portada.

```
Astro (estático) ─── Nginx ─── Gunicorn ─── Django + DRF ─── SQLite (WAL)
       │                                          │
   islas React                            /proc del host (métricas)
```

---

## Arranque rápido

```bash
make init         # genera .env, construye e inicializa todo
make superuser    # crea el usuario del admin
make seed         # carga el contenido inicial desde el CV
```

- API → http://localhost:8000/api/v1/
- Admin → http://localhost:8000/admin/
- Web → http://localhost:4321

`make` sin argumentos lista todos los comandos disponibles.

---

## Estructura

```
MySite/
├── apps/
│   ├── api/          Django + DRF · 6 módulos de dominio
│   └── web/          Astro + islas React
├── infra/
│   ├── docker/       api.Dockerfile · web.Dockerfile
│   ├── nginx/        nginx.conf · site.conf · cabeceras · proxy
│   ├── compose.prod.yml
│   ├── scripts/      droplet-setup · init-ssl · backup · init-env
│   └── workflows/    ci · deploy · content-rebuild  ← copiar a .github/
└── docs/             la documentación real del sistema
```

> **Integración continua.** Los workflows viven en `.github/workflows/`, la
> única ruta donde GitHub Actions los busca. `ci.yml` corre en cada push y
> pull request; `deploy.yml` despliega al empujar a `main` y se omite solo
> mientras no exista el secreto `DROPLET_HOST`, de modo que el repositorio
> no acumula fallos por un servidor que todavía no existe.

---

## La restricción que explica todo el diseño

El destino tiene **512 MB de RAM**. Medido sobre la pila de producción real:
Django consume **104 MB** y Nginx **3,6 MB**; con Ubuntu y el daemon de Docker
(~200 MB estimados) el total ronda los **308 MB**, dejando ~204 MB de margen.
De ahí salen tres reglas que no se negocian:

1. **El droplet nunca compila.** Un build de Astro pide 400–800 MB de pico.
   Todo build vive en GitHub Actions.
2. **Ni Redis, ni Postgres, ni Node en producción.** Caché en proceso,
   SQLite en modo WAL y HTML estático servido por Nginx.
3. **Los logs de Docker se rotan siempre.** Sin rotación, llenan los 10 GB de
   disco en semanas. Es la caída más común y más tonta en droplets pequeños.

---

## Documentación

| Documento | Qué contiene |
|---|---|
| [architecture.md](docs/architecture.md) | Presupuesto de RAM, capas, i18n, métricas del host, seguridad |
| [database.md](docs/database.md) | Esquema, índices, anti-trampa, respaldos |
| [api.md](docs/api.md) | Contrato v1, límites de peticiones, formatos de error |
| [modules.md](docs/modules.md) | Los 12 módulos y la definición de completado |
| [deployment.md](docs/deployment.md) | De un droplet vacío a producción, paso a paso |
| [decisions.md](docs/decisions.md) | ADRs — cada decisión **con su costo anotado** |
| [mobile_flow.md](docs/mobile_flow.md) | Estrategia móvil y presupuesto de rendimiento |

---

## Calidad

```bash
make test     # 71 pruebas
make lint     # ruff + black
make format
```

En el frontend: `npm run check` (tipos) y `npm run lint` (Prettier).

CI ejecuta las dos baterías más `manage.py check --deploy`, que verifica los
ajustes de seguridad de producción antes de que lleguen a producción.

---

## Licencia

Código bajo MIT. El contenido —textos, CV, imágenes de los proyectos— es
propiedad de Pedro Mamani Tito.
