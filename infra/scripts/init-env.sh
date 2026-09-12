#!/usr/bin/env sh
# Crea .env a partir de .env.example, sustituyendo los marcadores de
# secreto por valores aleatorios reales.
#
# Idempotente: si .env ya existe, no lo toca. Sobrescribir el .env de
# alguien y llevarse por delante sus credenciales es imperdonable.

set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
EXAMPLE="$ROOT/.env.example"
TARGET="$ROOT/.env"

if [ -f "$TARGET" ]; then
    echo "→ .env ya existe, no se modifica."
    exit 0
fi

if [ ! -f "$EXAMPLE" ]; then
    echo "✗ No se encuentra .env.example en $ROOT" >&2
    exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
    echo "✗ openssl no está disponible; no se pueden generar secretos." >&2
    exit 1
fi

cp "$EXAMPLE" "$TARGET"

# Cada marcador se reemplaza línea a línea con un secreto DISTINTO.
# Reutilizar la misma clave para firmar tokens y para hashear IPs anula
# el aislamiento entre ambos mecanismos.
TMP="$(mktemp)"
while IFS= read -r line; do
    case "$line" in
        *cambiame*) 
            key="${line%%=*}"
            printf '%s=%s\n' "$key" "$(openssl rand -hex 32)" >> "$TMP"
            ;;
        *) printf '%s\n' "$line" >> "$TMP" ;;
    esac
done < "$TARGET"
mv "$TMP" "$TARGET"
chmod 600 "$TARGET"

echo "✓ .env creado con secretos aleatorios (permisos 600)."
echo "  Falta rellenar a mano: EMAIL_HOST_PASSWORD y GITHUB_DISPATCH_TOKEN."
