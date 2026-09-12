#!/usr/bin/env bash
#
# Proxy mínimo para el PRIMER despliegue. Se usa una sola vez.
#
# El problema que resuelve:
#
#   El sitio se construye en GitHub Actions consultando la API por
#   https://pedrinidev.com/api/v1 — así las páginas salen prerenderizadas.
#   Pero quien atiende ese HTTPS es Nginx, y Nginx viaja DENTRO de la imagen
#   del sitio. O sea: para construir el sitio hace falta el sitio.
#
#   En un servidor ya en marcha no se nota, porque siempre hay una versión
#   anterior sirviendo. Solo muerde la primera vez.
#
# Este script levanta un Nginx genérico —ninguna imagen nuestra— que expone
# únicamente /api/ con el certificado ya emitido. Con eso el build consigue
# los datos, publica la imagen del sitio, y el despliegue la levanta encima.
# El contenedor se retira solo en cuanto deja de hacer falta.
set -euo pipefail

DOMAIN="${DOMAIN:-pedrinidev.com}"
NAME="mysite-bootstrap-proxy"
HERE="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$HERE/compose.prod.yml"
[ -f "$COMPOSE_FILE" ] || COMPOSE_FILE="$HERE/../compose.prod.yml"
NET="$(docker network ls --format '{{.Name}}' | grep -E 'internal$' | head -1)"

case "${1:-up}" in
  up)
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    CONF=$(mktemp)
    cat > "$CONF" <<NGINX
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen 443 ssl;
    http2 on;
    server_name ${DOMAIN} www.${DOMAIN};

    ssl_certificate     /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    # Solo la API. Todo lo demás responde 503 a propósito: este proxy no
    # sirve el sitio, y devolver una página en blanco confundiría más.
    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    location / { return 503; }
}
NGINX
    docker run -d --name "$NAME" --network "$NET" \
        -p 80:80 -p 443:443 \
        -v mysite_certbot_conf:/etc/letsencrypt:ro \
        -v "$CONF":/etc/nginx/conf.d/default.conf:ro \
        nginx:1.27-alpine >/dev/null
    sleep 3
    echo "✓ Proxy temporal en pie. Comprobación:"
    curl -s -o /dev/null -w "  https://${DOMAIN}/api/v1/projects/ -> %{http_code}\n" \
        "https://${DOMAIN}/api/v1/projects/?lang=es" || true
    echo "  Lanzá ahora el workflow Deploy. Al terminar: $0 down"
    ;;
  down)
    docker rm -f "$NAME" >/dev/null 2>&1 && echo "✓ Proxy temporal retirado" \
        || echo "  no estaba en pie"
    ;;
  *) echo "uso: $0 [up|down]" >&2; exit 1 ;;
esac
