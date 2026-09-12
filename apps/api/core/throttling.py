"""Limitación de peticiones.

Dos cachés distintas, y la razón importa.

**Lecturas → caché de proceso (`default`, LocMemCache).**
El límite general es de 60/min y existe para frenar rastreadores agresivos,
no para contar con precisión. Con 2 workers de Gunicorn el límite efectivo es
de 120/min, que sigue cumpliendo el objetivo. A cambio, cada lectura se ahorra
las ~5 consultas a SQLite que costaba llevar la cuenta en base de datos: en un
endpoint que se consulta cada 15 segundos desde cada visitante, eso es
escritura constante sobre el disco para nada.

**Escrituras → caché compartida (`throttle`, DatabaseCache).**
Aquí la precisión sí importa: «3 mensajes por hora» que en realidad son 6
—uno por worker— deja de ser un límite. Son endpoints de volumen bajísimo, así
que el coste en consultas es irrelevante.

Todas identifican al cliente por `X-Real-IP`, que Nginx sobrescribe y el
cliente no puede falsificar.
"""

from __future__ import annotations

import secrets

from django.conf import settings
from django.core.cache import caches
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from core.security import client_ip

# Nombre de la cabecera en el formato de WSGI, no un secreto.
BUILD_TOKEN_HEADER = "HTTP_X_BUILD_TOKEN"  # noqa: S105


def is_build_request(request) -> bool:
    """¿Viene esta petición del proceso que prerenderiza el sitio?

    El build de Astro hace ~30 peticiones en segundos desde una sola IP, que
    es justo el patrón que el límite anónimo existe para frenar. Sin esta
    exención, el propio despliegue se autobloquea con un 429.

    La comparación es en tiempo constante: comparar secretos con `==` filtra
    información sobre el prefijo correcto a través del tiempo de respuesta.
    Aquí el riesgo es pequeño, pero comparar secretos bien no cuesta nada y
    no hacerlo es una costumbre que acaba pagándose en otro sitio.
    """
    expected = settings.BUILD_API_TOKEN
    if not expected:
        return False
    provided = request.META.get(BUILD_TOKEN_HEADER, "")
    return bool(provided) and secrets.compare_digest(provided, expected)


class SharedAnonRateThrottle(AnonRateThrottle):
    """Límite general de lectura. Caché de proceso: barato y suficiente."""

    cache = caches["default"]

    def allow_request(self, request, view) -> bool:
        if is_build_request(request):
            return True
        return super().allow_request(request, view)

    def get_ident(self, request) -> str:
        return client_ip(request)


class ScopedIPThrottle(SimpleRateThrottle):
    """Base para límites de ESCRITURA, con estado compartido entre workers."""

    cache = caches["throttle"]
    scope = "anon"

    def get_cache_key(self, request, view) -> str:
        return self.cache_format % {"scope": self.scope, "ident": client_ip(request)}


class ContactThrottle(ScopedIPThrottle):
    """3 mensajes por hora. Un humano no necesita más; un bot sí."""

    scope = "contact"


class GameSessionThrottle(ScopedIPThrottle):
    scope = "game-session"


class ScoreSubmitThrottle(ScopedIPThrottle):
    scope = "score"


class SearchThrottle(SimpleRateThrottle):
    """La búsqueda hace LIKE sobre el cuerpo de los posts: más cara que un
    listado normal y por eso con su propio límite.

    Es una lectura, así que va a la caché de proceso como el resto de lecturas.
    """

    cache = caches["default"]
    scope = "search"

    def allow_request(self, request, view) -> bool:
        if is_build_request(request):
            return True
        return super().allow_request(request, view)

    def get_cache_key(self, request, view) -> str:
        return self.cache_format % {"scope": self.scope, "ident": client_ip(request)}
