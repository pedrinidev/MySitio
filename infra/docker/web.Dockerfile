# syntax=docker/dockerfile:1
#
# Frontend: build de Astro + Nginx sirviéndolo.
#
# La etapa de build corre en GitHub Actions, NUNCA en el droplet: Vite tiene
# picos de 400-800 MB de RAM y el destino tiene 512 MB en total.
# Ver docs/decisions.md, ADR-002.
#
# La imagen final es nginx:alpine con el dist copiado dentro: ~25 MB, y
# desplegar es cambiar de tag. Node no llega a producción.

# ───────────────────────── builder ──────────────────────────
FROM node:24-alpine AS builder

WORKDIR /app

# La URL de la API entra como argumento de build porque Astro la incrusta en
# el HTML generado: es una decisión de tiempo de compilación, no de ejecución.
ARG PUBLIC_API_URL=https://pedrinidev.com/api/v1
ARG PUBLIC_SITE_URL=https://pedrinidev.com

# Dirección por la que el PROCESO DE BUILD alcanza la API, que no tiene por
# qué ser la misma que usará el navegador. En producción coinciden y esta
# queda vacía; hace falta cuando se construye desde dentro de una red
# privada —o desde esta misma máquina— donde la URL pública no resuelve.
ARG INTERNAL_API_URL=
ENV PUBLIC_API_URL=$PUBLIC_API_URL \
    PUBLIC_SITE_URL=$PUBLIC_SITE_URL \
    INTERNAL_API_URL=$INTERNAL_API_URL \
    ASTRO_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

# El contexto de build es la RAÍZ del monorepo, no apps/web: la etapa final
# necesita infra/nginx/. Por eso todas las rutas van completas desde la raíz.
#
# package*.json primero: mientras las dependencias no cambien, esta capa se
# reutiliza y el build se salta la instalación entera.
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY apps/web/ ./

# Astro consulta la API de Django AQUÍ para prerenderizar cada página.
# Si la API no responde, el cliente lanza y el build falla a propósito:
# publicar el sitio con las secciones vacías sería peor que no publicarlo.
#
# El token va como SECRETO de BuildKit y NO como build-arg. La diferencia es
# de seguridad, no de estilo: los build-args quedan grabados en el historial
# de la imagen (`docker history`) y, con el repositorio público, cualquiera
# podría leerlos desde GHCR. Un `--mount=type=secret` existe solo durante
# este RUN y no deja rastro en ninguna capa.
#
# Sin el token el build funciona igual, pero la API puede devolverle 429:
# prerenderizar el sitio son ~22 peticiones en pocos segundos desde una sola
# IP, justo el patrón que el límite anónimo existe para frenar.
RUN --mount=type=secret,id=build_token \
    BUILD_API_TOKEN="$(cat /run/secrets/build_token 2>/dev/null || true)" \
    npm run build:ci

# Comprobación explícita: un dist vacío no debe llegar nunca a una imagen.
RUN test -f dist/es/index.html && test -f dist/en/index.html \
    || (echo "✗ El build no generó las páginas esperadas" && exit 1)

# ────────────────────────── runtime ─────────────────────────
FROM nginx:1.27-alpine AS prod

RUN apk add --no-cache curl tzdata

COPY --from=builder /app/dist /srv/web
COPY infra/nginx/nginx.conf /etc/nginx/nginx.conf
# Como PLANTILLA y no como configuración final: el arranque de la imagen
# oficial de Nginx ejecuta envsubst sobre /etc/nginx/templates/*.template y
# escribe el resultado en conf.d/. Así la ruta del admin se resuelve al
# levantar el contenedor y no queda grabada en la imagen — que es pública.
COPY infra/nginx/site.conf /etc/nginx/templates/default.conf.template
COPY infra/nginx/proxy_params.conf /etc/nginx/proxy_params.conf
COPY infra/nginx/security_headers.conf /etc/nginx/security_headers.conf

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
