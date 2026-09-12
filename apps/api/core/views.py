"""Endpoints transversales."""

from __future__ import annotations

import logging

from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

logger = logging.getLogger("mysite.health")


@api_view(["GET"])
@throttle_classes([])  # el healthcheck de Docker corre cada 30 s: no debe limitarse
def health(request) -> Response:
    """Comprobación de salud usada por Docker y por el despliegue.

    Consulta la base de datos a propósito. Un healthcheck que solo devuelve
    "ok" confirma que el proceso de Python vive, que es justo lo que nunca
    falla — el fallo real es un volumen no montado o una base corrupta.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Healthcheck: la base de datos no responde")
        return Response(
            {"status": "unhealthy", "database": "down"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({"status": "ok", "database": "up"})
