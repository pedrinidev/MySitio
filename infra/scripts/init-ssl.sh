#!/usr/bin/env bash
#
# Emisión inicial del certificado TLS.
#
# Se ejecuta UNA vez, en el droplet, cuando el DNS ya apunta aquí. Después,
# las renovaciones las hace el cron (ver droplet-setup.sh).
#
# El problema del huevo y la gallina: Nginx no arranca sin certificado, y
# Certbot no puede validar el dominio sin un Nginx que responda por HTTP.
# Se resuelve emitiendo primero un certificado autofirmado temporal, dejando
# que Nginx arranque, y sustituyéndolo después por el real.

set -euo pipefail

DOMAIN="${DOMAIN:-pedrinidev.com}"
EMAIL="${LETSENCRYPT_EMAIL:-pedrinidevs@gmail.com}"
# El compose está JUNTO a este script en el servidor (/srv/mysite) y un
# nivel más arriba en el repositorio (infra/scripts → infra/). Se busca en
# ese orden para que el mismo archivo sirva en los dos sitios: antes tenía
# la ruta del repositorio fija y en el droplet apuntaba a /srv/, que no
# existe.
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$HERE/compose.prod.yml" ]; then
    COMPOSE_FILE="$HERE/compose.prod.yml"
elif [ -f "$HERE/../compose.prod.yml" ]; then
    COMPOSE_FILE="$HERE/../compose.prod.yml"
else
    echo "✗ No encuentro compose.prod.yml junto a este script ni un nivel arriba." >&2
    exit 1
fi
COMPOSE="docker compose -f $COMPOSE_FILE"
STAGING="${STAGING:-0}"

echo "→ Emitiendo certificado para $DOMAIN y www.$DOMAIN"

if [ "$STAGING" = "1" ]; then
    echo "  (modo staging: certificado de prueba, sin gastar cuota real)"
    STAGING_FLAG="--staging"
else
    STAGING_FLAG=""
fi

# ── 1. Terreno despejado ───────────────────────────────────────────────
#
# Antes aquí se creaba un certificado autofirmado temporal, para que Nginx
# pudiera arrancar y servir el reto ACME. Con `--standalone` eso ya no hace
# falta, y además estorbaba: Certbot se niega a emitir si ya existe un
# directorio `live/` para el dominio («live directory exists»).
#
# Solo se limpia lo que dejó una ejecución anterior fallida, nunca un
# certificado bueno: si el que hay es de verdad, `--force-renewal` lo
# renueva sin que haya que borrar nada.
if $COMPOSE run --rm --entrypoint sh certbot -c \
        "[ -f /etc/letsencrypt/live/$DOMAIN/fullchain.pem ] && \
         openssl x509 -in /etc/letsencrypt/live/$DOMAIN/fullchain.pem -noout -issuer | grep -qi 'CN *= *localhost'" 2>/dev/null; then
    echo "→ Retirando el certificado autofirmado de un intento anterior…"
    $COMPOSE run --rm --entrypoint sh certbot -c \
        "rm -rf /etc/letsencrypt/live/$DOMAIN /etc/letsencrypt/archive/$DOMAIN /etc/letsencrypt/renewal/$DOMAIN.conf"
fi

# ── 2. Certificado real, con Certbot sirviendo el reto por su cuenta ───
#
# `--standalone` y NO `--webroot`, y la diferencia es la que desbloquea todo
# el despliegue inicial:
#
# `--webroot` deja el reto en un directorio que tiene que servir Nginx. Pero
# Nginx vive en la imagen del sitio, y esa imagen se construye consultando
# la API por HTTPS… que no existe hasta que haya certificado. Circular: para
# emitir el primer certificado harían falta cosas que solo existen después
# de emitirlo.
#
# `--standalone` levanta un servidor mínimo propio en el puerto 80 durante
# los segundos que dura la validación. No depende de ninguna imagen nuestra,
# así que el arranque en frío deja de ser un problema.
#
# Las RENOVACIONES sí usan webroot a través de Nginx (ver el cron en
# droplet-setup.sh): para entonces Nginx ya está en pie y no conviene parar
# el sitio cada 60 días.
echo "→ Liberando el puerto 80 para la validación…"
$COMPOSE stop web 2>/dev/null || true

echo "→ Solicitando el certificado a Let's Encrypt…"
$COMPOSE run --rm -p 80:80 certbot certonly \
    --standalone \
    --email "$EMAIL" \
    --agree-tos --no-eff-email \
    --force-renewal \
    $STAGING_FLAG \
    -d "$DOMAIN" -d "www.$DOMAIN"

# ── 3. Nginx con el certificado bueno ──────────────────────────────────
#
# Puede que la imagen del sitio todavía no exista: en el primer despliegue
# el certificado se emite ANTES de que se pueda construir. No es un fallo —
# el siguiente despliegue la publica y la levanta. Por eso este paso avisa
# en lugar de abortar.
echo "→ Levantando Nginx con el certificado…"
if $COMPOSE up -d web 2>/dev/null; then
    sleep 3
    $COMPOSE exec -T web nginx -s reload 2>/dev/null || true
    echo "✓ TLS activo en https://$DOMAIN"
else
    echo "✓ Certificado emitido y guardado."
    echo "  La imagen del sitio aún no existe; se levantará en el próximo"
    echo "  despliegue. Lanzá el workflow Deploy y quedará servido."
fi
echo "  Comprobalo en https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
