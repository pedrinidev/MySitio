"""Disparo de la reconstrucción del sitio estático.

El frontend es HTML compilado: publicar contenido en el admin no cambia nada
hasta que GitHub Actions vuelve a construirlo. Este módulo es el puente.

Tres decisiones que merecen explicación:

* Se dispara con `transaction.on_commit`, no dentro del `save()`. Si la
  transacción se revierte, no queremos haber lanzado un despliegue de
  contenido que no existe.
* Se agrupa con una ventana de 60 s. Editar cinco posts seguidos debe producir
  una reconstrucción, no cinco — cada una consume minutos de GitHub Actions.
* Un fallo **nunca** se propaga. Que GitHub esté caído no puede impedir que el
  autor guarde su trabajo.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.cache import caches
from django.db import transaction

logger = logging.getLogger("mysite.webhooks")

_DEBOUNCE_KEY = "rebuild:debounce"
_DEBOUNCE_SECONDS = 60
_REQUEST_TIMEOUT = 5


def schedule_site_rebuild(reason: str) -> None:
    """Programa una reconstrucción para cuando la transacción actual confirme."""
    if not settings.REBUILD_WEBHOOK_ENABLED:
        logger.debug("Reconstrucción desactivada; se ignora: %s", reason)
        return
    transaction.on_commit(lambda: _dispatch(reason))


def _dispatch(reason: str) -> None:
    cache = caches["throttle"]
    # `add` atómico: si la clave ya existe, otra edición reciente ya disparó
    # la reconstrucción y esta se agrupa con aquella.
    if not cache.add(_DEBOUNCE_KEY, True, timeout=_DEBOUNCE_SECONDS):
        logger.info("Reconstrucción agrupada con una anterior (%s)", reason)
        return

    url = f"https://api.github.com/repos/{settings.GITHUB_REPOSITORY}/dispatches"
    try:
        response = requests.post(
            url,
            json={"event_type": "content-updated", "client_payload": {"reason": reason}},
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {settings.GITHUB_DISPATCH_TOKEN}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=_REQUEST_TIMEOUT,
        )
        if response.status_code == 204:
            logger.info("Reconstrucción solicitada correctamente (%s)", reason)
        else:
            logger.error(
                "GitHub rechazó la reconstrucción: %s %s",
                response.status_code,
                response.text[:200],
            )
    except requests.RequestException as exc:
        # Se registra y se sigue: el contenido ya está guardado y se publicará
        # en el siguiente despliegue.
        logger.error("No se pudo contactar con GitHub para reconstruir: %s", exc)
