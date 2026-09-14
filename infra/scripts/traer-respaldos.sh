#!/usr/bin/env bash
#
# Trae los respaldos del droplet a este equipo.
#
# POR QUÉ EXISTE
#
# El cron del servidor genera un respaldo cada noche, pero lo deja EN EL
# MISMO servidor que protege. Eso cubre un borrado accidental o una
# migración mal aplicada; no cubre perder el droplet. Si DigitalOcean tiene
# un incidente o la cuenta se cierra, se van la base, las portadas, el CV y
# los mensajes de contacto junto con sus copias.
#
# POR QUÉ NO ES UN `rsync` DIRECTO
#
# Lo natural sería `rsync` contra la carpeta del volumen:
#
#     /var/lib/docker/volumes/mysite_api_data/_data/backups
#
# pero ese árbol es de root (`drwx--x---`) y el usuario `deploy` no puede
# leerlo. Sí puede hablar con Docker, así que se lanza un contenedor mínimo
# que empaqueta la carpeta y la escupe por la salida estándar; el túnel de
# SSH la trae y se desempaqueta aquí. Sin sudo, sin tocar permisos del
# servidor y sin abrir nada.
#
# El coste de no ser incremental es irrelevante: son unos 5 MB.
#
#     ./traer-respaldos.sh                  # a ~/Respaldos/pedrinidev
#     ./traer-respaldos.sh /otra/carpeta
#
# AUTOMATIZADO
#
# Hay un agente de launchd que lo ejecuta a diario. Apunta a una COPIA en
# ~/bin y no a este archivo: macOS protege ~/Desktop, y una tarea programada
# que intente leer ahí recibe «Operation not permitted» y falla en silencio
# todos los días. Para propagar un cambio de este guion:
#
#     cp infra/scripts/traer-respaldos.sh ~/bin/pedrinidev-respaldos.sh

set -euo pipefail

SERVIDOR="${SERVIDOR:-deploy@137.184.219.198}"
CLAVE="${CLAVE:-$HOME/.ssh/pedrinidev}"
VOLUMEN="${VOLUMEN:-mysite_api_data}"
DESTINO="${1:-$HOME/Respaldos/pedrinidev}"

mkdir -p "$DESTINO"

echo "→ Trayendo respaldos de $SERVIDOR"

# `-C /data backups` empaqueta la carpeta con su nombre; `--strip-components=1`
# lo quita al desempaquetar para que los archivos caigan sueltos en el destino.
ssh -i "$CLAVE" "$SERVIDOR" \
    "docker run --rm -v ${VOLUMEN}:/data:ro alpine tar -cz -C /data backups" \
  | tar -xz -C "$DESTINO" --strip-components=1

# Verificación: un respaldo que nadie comprueba no es un respaldo.
# Se descomprime el más reciente y se le pide a SQLite que se revise.
ULTIMO=$(ls -1t "$DESTINO"/db-*.sqlite3.gz 2>/dev/null | head -1 || true)
if [ -z "$ULTIMO" ]; then
  echo "✗ No llegó ninguna copia de la base de datos." >&2
  exit 1
fi

TEMPORAL=$(mktemp)
trap 'rm -f "$TEMPORAL"' EXIT
gunzip -c "$ULTIMO" > "$TEMPORAL"

if command -v sqlite3 >/dev/null 2>&1; then
  ESTADO=$(sqlite3 "$TEMPORAL" "PRAGMA integrity_check" 2>&1 | head -1)
else
  # macOS no siempre trae el binario `sqlite3`, pero Python sí el módulo.
  ESTADO=$(python3 - "$TEMPORAL" <<'PY'
import sqlite3, sys
print(sqlite3.connect(sys.argv[1]).execute("PRAGMA integrity_check").fetchone()[0])
PY
)
fi

# ── ¿Sigue vivo el cron del servidor? ────────────────────────────────
#
# El aviso por Telegram de `backup.sh` cubre que el respaldo FALLE. No cubre
# que deje de ejecutarse: si el cron muere, el guion nunca corre y por tanto
# nunca avisa. El único síntoma es que las copias dejan de aparecer, y eso
# solo se nota desde fuera.
#
# Dos días de margen: si el Mac estuvo apagado el fin de semana la copia más
# reciente puede tener un día, y eso es normal.
EDAD_DIAS=$(( ( $(date +%s) - $(stat -f %m "$ULTIMO" 2>/dev/null || stat -c %Y "$ULTIMO") ) / 86400 ))
if [ "$EDAD_DIAS" -gt 2 ]; then
  echo "⚠  La copia más reciente tiene $EDAD_DIAS días: el cron del servidor puede estar parado." >&2
  echo "   Comprobalo con:  ssh droplet 'tail /srv/mysite/backup.log'" >&2
fi

TOTAL=$(du -sh "$DESTINO" | cut -f1)
COPIAS=$(ls -1 "$DESTINO"/db-*.sqlite3.gz 2>/dev/null | wc -l | tr -d ' ')

echo "✓ $COPIAS copias en $DESTINO ($TOTAL)"
echo "  la más reciente: $(basename "$ULTIMO") · integridad: $ESTADO"

[ "$ESTADO" = "ok" ] || { echo "✗ La copia más reciente NO pasa la comprobación." >&2; exit 1; }
