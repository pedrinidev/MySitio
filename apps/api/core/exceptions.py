"""Manejo de errores unificado de la API.

Un frontend solo puede tratar los errores bien si todos tienen la misma forma.
Aquí se garantiza que cualquier fallo —de validación, de permisos o inesperado—
llegue como el mismo objeto JSON.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("mysite.api")


class ServiceError(APIException):
    """Fallo controlado de la capa de servicios.

    Permite que un servicio señale un problema de dominio sin importar DRF
    en toda la capa de negocio... y sin devolver `None` y rezar.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "No se pudo completar la operación."
    default_code = "service_error"


class ExternalServiceUnavailable(ServiceError):
    """Una dependencia externa (SMTP, GitHub) no respondió."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "El servicio no está disponible en este momento."
    default_code = "service_unavailable"


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Normaliza toda respuesta de error a `{detail, code, errors}`."""
    # Las ValidationError de Django (lanzadas desde model.clean()) no las
    # entiende DRF por sí solo: se traducen antes de delegar.
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(detail=getattr(exc, "message_dict", exc.messages))

    response = drf_exception_handler(exc, context)

    if response is None:
        # Excepción no controlada: 500. Se registra con traza completa, pero
        # al cliente solo le llega un mensaje genérico — un stacktrace en la
        # respuesta es un regalo para quien esté buscando por dónde entrar.
        view = context.get("view")
        logger.exception("Error no controlado en %s", view.__class__.__name__ if view else "?")
        return Response(
            {
                "detail": "Error interno del servidor.",
                "code": "internal_error",
                "errors": {},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, Http404):
        payload = {"detail": "No se encontró el recurso solicitado.", "code": "not_found"}
        errors: dict[str, Any] = {}
    elif isinstance(exc, ValidationError):
        payload = {"detail": "Los datos enviados no son válidos.", "code": "validation_error"}
        errors = response.data if isinstance(response.data, dict) else {"non_field": response.data}
    else:
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        # DRF envuelve el mensaje en un ErrorDetail, que es un str con un
        # atributo `.code`. Ahí es donde acaba el código que pasó quien lanzó
        # la excepción; `exc.default_code` solo tiene el de la clase y perdería
        # la distinción entre, por ejemplo, "invalid_session" e
        # "implausible_score" — justo lo que el frontend necesita para saber
        # si reintentar o mostrar un mensaje distinto.
        payload = {
            "detail": str(detail) if detail else "La petición no pudo procesarse.",
            "code": getattr(detail, "code", None) or getattr(exc, "default_code", "error"),
        }
        errors = {}

    response.data = {**payload, "errors": errors}
    return response
