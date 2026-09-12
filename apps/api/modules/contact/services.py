"""Procesamiento de los mensajes de contacto.

Orden de operaciones, y el porqué: **guardar primero, avisar después.**
Si el canal de aviso falla, el mensaje ya está en la base y se ve en el
admin. Al revés —avisar y luego guardar— un fallo de red haría desaparecer
el mensaje sin que nadie se entere.

Este módulo decide *qué* se dice en el aviso, no por dónde sale: de eso se
encarga ``core.notifications``.
"""

from __future__ import annotations

import logging

from django.conf import settings

from core.notifications import Notification, send_notification
from modules.contact.models import ContactMessage, MessageStatus

logger = logging.getLogger("mysite.contact")


def is_likely_bot(*, honeypot: str, elapsed_ms: int) -> bool:
    """Heurística anti-spam sin captchas ni servicios de terceros.

    Dos señales:
    * El campo señuelo viene relleno — un humano no puede verlo.
    * El formulario se envió demasiado rápido para haberlo escrito.

    Ninguna molesta al visitante ni depende de un servicio externo, que en un
    droplet de 512 MB es exactamente lo que queremos evitar.
    """
    if honeypot.strip():
        logger.info("Contacto descartado: honeypot relleno")
        return True
    if 0 < elapsed_ms < settings.CONTACT_MIN_ELAPSED_MS:
        logger.info("Contacto descartado: enviado en %d ms", elapsed_ms)
        return True
    return False


def create_message(
    *,
    data: dict,
    ip_hash: str,
    user_agent: str,
    flagged_as_bot: bool,
) -> ContactMessage:
    """Persiste el mensaje. Los sospechosos entran marcados como spam.

    No se descartan sin guardar: si la heurística se equivoca, el mensaje
    sigue estando y solo hace falta reclasificarlo desde el admin.
    """
    return ContactMessage.objects.create(
        name=data["name"].strip(),
        email=data["email"].strip(),
        subject=data["subject"].strip(),
        message=data["message"].strip(),
        locale=data.get("locale", "es"),
        status=MessageStatus.SPAM if flagged_as_bot else MessageStatus.NEW,
        ip_hash=ip_hash,
        user_agent=user_agent[:300],
    )


def build_notification(message: ContactMessage) -> Notification:
    """Arma el aviso en datos, sin maquetar: cada canal lo pinta a su manera.

    El asunto va también como campo de la cabecera porque Telegram no tiene
    línea de asunto donde mostrarlo, y es lo primero que se quiere leer.
    """
    return Notification(
        subject=f"[pedrinidev.com] {message.subject}",
        title="Nuevo mensaje desde el portafolio",
        fields=(
            ("Nombre", message.name),
            ("Correo", message.email),
            ("Asunto", message.subject),
            ("Idioma", message.locale),
            ("Fecha", f"{message.created_at:%Y-%m-%d %H:%M}"),
        ),
        text=message.message,
        reply_to=message.email,
    )


def notify(message: ContactMessage) -> bool:
    """Envía el aviso por el canal configurado. Devuelve si se entregó.

    Nunca lanza excepción: el mensaje ya está guardado y un fallo del canal
    no debe convertirse en un error de cara al visitante.
    """
    if message.status == MessageStatus.SPAM:
        return False

    try:
        send_notification(build_notification(message))
    except Exception as exc:
        logger.error("No se pudo enviar la notificación del mensaje %s: %s", message.pk, exc)
        return False

    ContactMessage.objects.filter(pk=message.pk).update(delivered=True)
    logger.info("Notificación enviada para el mensaje %s", message.pk)
    return True
