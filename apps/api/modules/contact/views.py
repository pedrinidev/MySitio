from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from core.security import request_ip_hash
from core.throttling import ContactThrottle
from modules.contact import services
from modules.contact.serializers import ContactMessageSerializer


@api_view(["POST"])
@throttle_classes([ContactThrottle])
def create_contact_message(request) -> Response:
    """Recibe el formulario de contacto.

    Detalle deliberado: a un bot detectado se le responde **201, igual que a
    un humano**. Devolverle un error le enseña qué señal lo delató y le
    permite ajustarse. El silencio no.
    """
    payload = ContactMessageSerializer(data=request.data)
    payload.is_valid(raise_exception=True)
    data = payload.validated_data

    flagged = services.is_likely_bot(
        honeypot=data.pop("website", ""),
        elapsed_ms=data.pop("elapsed_ms", 0),
    )

    message = services.create_message(
        data=data,
        ip_hash=request_ip_hash(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        flagged_as_bot=flagged,
    )
    services.notify(message)

    return Response(
        {"detail": "Mensaje recibido. Gracias por escribir."},
        status=status.HTTP_201_CREATED,
    )
