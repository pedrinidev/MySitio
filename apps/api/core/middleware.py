"""Middleware propio del proyecto."""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

# Direcciones desde las que puede venir una comprobación de salud interna.
# Son las del propio contenedor: nada que llegue de fuera puede presentarlas,
# porque el origen lo pone el kernel y no la petición.
LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})

HEALTH_PATH = "/api/v1/health/"


class LoopbackHealthHostMiddleware:
    """Deja pasar el healthcheck local sin relajar ``ALLOWED_HOSTS``.

    El problema que resuelve:

    Docker, Compose y el paso de despliegue comprueban la salud pidiendo a
    ``http://127.0.0.1:8000/api/v1/health/`` desde dentro del contenedor.
    Django rechaza esa petición con ``DisallowedHost`` porque ``127.0.0.1``
    no está en ``ALLOWED_HOSTS`` — y hace bien en rechazarla.

    La solución tentadora es añadir ``127.0.0.1`` a ``ALLOWED_HOSTS``, y es
    un error: Nginx reenvía la cabecera ``Host`` **tal como la manda el
    cliente** (ver ``infra/nginx/proxy_params.conf``), así que cualquiera
    desde internet podría enviar ``Host: 127.0.0.1`` y saltarse la
    validación. Esa validación existe para evitar que una cabecera falsa
    acabe dentro de un enlace de recuperación de contraseña o de una
    respuesta cacheada.

    Por eso la excepción se acota por partida doble: solo la ruta de salud,
    y solo cuando la petición llega del propio host. Un atacante externo no
    puede cumplir la segunda condición — ``REMOTE_ADDR`` lo determina la
    conexión TCP, no lo que diga la petición.

    Va el PRIMERO de la lista de middleware: ``SecurityMiddleware`` llama a
    ``request.get_host()``, que es donde salta la excepción, de modo que la
    corrección tiene que ocurrir antes.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path == HEALTH_PATH and request.META.get("REMOTE_ADDR") in LOOPBACK:
            allowed = [h for h in settings.ALLOWED_HOSTS if h not in ("*", "")]
            if allowed:
                # Se sustituye por el primer host legítimo: la petición sigue
                # su curso normal y `get_host()` ya no lanza.
                request.META["HTTP_HOST"] = allowed[0]
        return self.get_response(request)
