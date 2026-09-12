"""Utilidades de seguridad transversales.

Dos principios que gobiernan este módulo:

1. **Nunca se almacena una IP en claro.** Se guarda su hash con sal. Sirve
   igual para limitar abuso y deja de ser un dato personal identificable.
2. **No se inventa criptografía.** La firma de tokens usa `django.core.signing`,
   que ya está auditado, en vez de un HMAC hecho a mano.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Any

from django.conf import settings
from django.core import signing
from django.core.cache import caches

logger = logging.getLogger("mysite.security")

_UNKNOWN_IP = "0.0.0.0"  # noqa: S104 — marcador, no una interfaz de escucha


def client_ip(request) -> str:
    """Obtiene la IP real del visitante detrás de Nginx.

    Se usa `X-Real-IP` y NO `X-Forwarded-For`. La diferencia es importante:
    `X-Forwarded-For` conserva lo que envió el cliente y le añade el salto
    real al final, así que un atacante puede inyectar entradas falsas. Nginx,
    en cambio, **sobrescribe** `X-Real-IP` con `$remote_addr`, que es la
    conexión TCP real y no se puede falsificar.

    Requiere que Nginx incluya `proxy_set_header X-Real-IP $remote_addr;`
    (ver infra/nginx/site.conf).
    """
    real_ip = request.META.get("HTTP_X_REAL_IP", "").strip()
    if real_ip:
        return real_ip
    return request.META.get("REMOTE_ADDR", _UNKNOWN_IP) or _UNKNOWN_IP


def hash_ip(ip: str) -> str:
    """Hash con sal de una IP, para limitar abuso sin guardar datos personales.

    La sal vive en `IP_HASH_SALT`. Sin ella el hash sería reversible: el
    espacio de IPv4 son 4.000 millones de valores y una tabla arcoíris se
    construye en minutos.
    """
    salt = settings.IP_HASH_SALT.encode("utf-8")
    return hashlib.sha256(salt + ip.encode("utf-8")).hexdigest()


def request_ip_hash(request) -> str:
    """Atajo: hash de la IP de la petición actual."""
    return hash_ip(client_ip(request))


def issue_signed_token(payload: dict[str, Any], *, salt: str) -> str:
    """Emite un token firmado y con marca de tiempo.

    Se le añade un identificador único (`jti`) para poder invalidarlo tras el
    primer uso. Sin él, un token válido podría reenviarse mil veces dentro de
    su ventana de validez.
    """
    data = {**payload, "jti": secrets.token_urlsafe(12)}
    return signing.dumps(data, key=settings.GAME_TOKEN_SECRET, salt=salt)


def consume_signed_token(token: str, *, salt: str, max_age: int) -> dict[str, Any] | None:
    """Valida un token y lo marca como usado. Devuelve None si no es utilizable.

    Un token se rechaza si está manipulado, si caducó o si ya se usó. La marca
    de uso vive en la caché compartida (SQLite), no en memoria del proceso:
    con dos workers de Gunicorn, una caché por proceso permitiría usar cada
    token dos veces.
    """
    try:
        data = signing.loads(token, key=settings.GAME_TOKEN_SECRET, salt=salt, max_age=max_age)
    except signing.SignatureExpired:
        logger.info("Token rechazado: caducado (salt=%s)", salt)
        return None
    except signing.BadSignature:
        logger.warning("Token rechazado: firma inválida (salt=%s)", salt)
        return None

    jti = data.get("jti")
    if not jti:
        return None

    cache = caches["throttle"]
    # `add` es atómico: devuelve False si la clave ya existía. Es la primitiva
    # correcta para "usar una sola vez"; un get seguido de set tendría una
    # ventana de carrera entre ambas operaciones.
    if not cache.add(f"token:used:{salt}:{jti}", True, timeout=max_age + 60):
        logger.warning("Token rechazado: ya se había usado (jti=%s)", jti)
        return None

    return data
