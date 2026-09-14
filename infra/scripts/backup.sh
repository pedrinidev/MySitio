#!/usr/bin/env bash
#
# Respaldo diario de la base de datos Y de los archivos subidos.
#
# Los dos, y no solo la base: las portadas de los proyectos, el CV y las
# imágenes del blog se suben desde el Admin y viven en /data/media. Un
# respaldo que guarde únicamente la base restauraría filas apuntando a
# archivos que ya no existen — el sitio volvería con todas las imágenes
# rotas y sin forma de recuperarlas. `seed_content` repone los textos, pero
# no puede reponer un archivo que nadie guardó.
#
# Usa la API de respaldo EN LÍNEA de SQLite, NO `cp`. La diferencia importa:
# copiar el archivo mientras hay una escritura en curso produce un respaldo
# corrupto que parece correcto hasta el día que hace falta restaurarlo.
#
# Se invoca desde el módulo `sqlite3` de Python y no desde el binario
# `sqlite3`, que NO está instalado en la imagen de la API — una imagen
# mínima a propósito. La versión anterior lo llamaba y fallaba con
# «sqlite3: not found» cada noche, en silencio, porque el cron manda la
# salida a /dev/null. Se descubrió ejecutándolo a mano; la carpeta de
# respaldos llevaba vacía desde el primer día.
#
# `Connection.backup()` es exactamente la misma API de respaldo en línea que
# usa el comando `.backup` del binario, así que no se pierde nada.

set -euo pipefail

APP_DIR="${APP_DIR:-/srv/mysite}"
COMPOSE="docker compose -f $APP_DIR/compose.prod.yml"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# ── Aviso de fallo ───────────────────────────────────────────────────
#
# Un respaldo que falla en silencio es peor que no tener respaldo: encima
# da confianza. Este guion lo ejecuta cron de madrugada, así que nadie ve
# su salida; escribirla en un registro solo traslada el problema a un
# archivo que tampoco se lee.
#
# Se avisa por Telegram, que es donde ya llegan los mensajes del
# formulario. Se manda por `curl` directo a la API y NO a través de Django:
# si la API está caída —una de las razones plausibles de que el respaldo
# falle— el aviso tiene que salir igual.
#
# Solo se avisa de los FALLOS. Un mensaje cada noche diciendo «todo bien»
# se silencia en una semana, y entonces el que importa pasa desapercibido.
avisar_fallo() {
    local codigo=$?
    [ "$codigo" -eq 0 ] && return 0

    local token chat
    token=$(grep -m1 "^TELEGRAM_BOT_TOKEN=" "$APP_DIR/.env" 2>/dev/null | cut -d= -f2-)
    chat=$(grep -m1 "^TELEGRAM_CHAT_ID=" "$APP_DIR/.env" 2>/dev/null | cut -d= -f2-)
    [ -n "$token" ] && [ -n "$chat" ] || return 0

    curl -s -m 15 -o /dev/null \
        "https://api.telegram.org/bot${token}/sendMessage" \
        -d "chat_id=${chat}" \
        -d "text=⚠️ El respaldo de pedrinidev.com FALLÓ (código ${codigo}) en $(hostname) a las $(date '+%H:%M del %d/%m'). Revisá: ssh droplet y luego cd /srv/mysite && ./backup.sh" \
        || true
}
trap avisar_fallo EXIT
STAMP="$(date +%F)"

cd "$APP_DIR"

$COMPOSE exec -T api python - <<PY
import pathlib
import sqlite3

pathlib.Path("/data/backups").mkdir(parents=True, exist_ok=True)

origen = sqlite3.connect("/data/db.sqlite3")
destino = sqlite3.connect("/data/backups/db-$STAMP.sqlite3")
try:
    with destino:
        origen.backup(destino)
finally:
    destino.close()
    origen.close()
PY

$COMPOSE exec -T api gzip -f "/data/backups/db-$STAMP.sqlite3"

# Archivos subidos. Se comprime la carpeta entera: son pocos megabytes y
# restaurar «la base y los archivos del mismo día» es mucho más simple que
# reconciliar dos historiales distintos.
$COMPOSE exec -T api sh -c "
    if [ -d /data/media ] && [ -n \"\$(ls -A /data/media 2>/dev/null)\" ]; then
        tar -czf /data/backups/media-$STAMP.tar.gz -C /data media
    fi
"

# Purga: sin esto, en un disco de 10 GB los respaldos acabarían provocando
# justo la caída que pretenden remediar.
$COMPOSE exec -T api sh -c "
    find /data/backups -name 'db-*.sqlite3.gz' -mtime +$RETENTION_DAYS -delete
    find /data/backups -name 'media-*.tar.gz' -mtime +$RETENTION_DAYS -delete
"

SIZE=$($COMPOSE exec -T api sh -c "du -sh /data/backups | cut -f1" | tr -d '\r')
echo "✓ Respaldo db-$STAMP.sqlite3.gz + media-$STAMP.tar.gz · carpeta: $SIZE"

# Los respaldos viven en el MISMO droplet. Protegen de un error humano o de
# una migración mal aplicada, NO de la pérdida del servidor. Para eso hace
# falta sacarlos fuera: DigitalOcean Spaces, otro servidor o el propio PC.
#
#   rsync -az deploy@pedrinidev.com:/var/lib/docker/volumes/mysite_api_data/_data/backups/ ./backups/
