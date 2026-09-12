"""Envío de correo por API HTTPS en lugar de SMTP.

Por qué existe este archivo:

DigitalOcean **bloquea el correo saliente** en los droplets — los puertos 25,
465, 587 y 2525 no responden, mientras que el 443 funciona con normalidad.
Es una medida antispam que aplican a las cuentas nuevas y no se puede
desactivar desde el servidor: ninguna configuración de Django, de Zoho ni
del cortafuegos cambia nada, porque el bloqueo está en la red del proveedor.

Se comprobó midiéndolo desde el propio droplet::

    puerto  25 → bloqueado      github:443 → abierto
    puerto 465 → bloqueado
    puerto 587 → bloqueado

La salida es no usar SMTP. Los servicios de correo transaccional ofrecen
una API HTTP que viaja por el 443 como cualquier otra petición, así que
atraviesa el bloqueo sin pedirle permiso a nadie.

Se implementa como un *backend* de correo de Django, no como una función
suelta, para que el resto del código no se entere: `EmailMessage.send()`
sigue funcionando igual y el módulo de contacto no cambia ni una línea.
Cambiar de proveedor —o volver a SMTP el día que se pueda— es cambiar una
variable de entorno.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage, EmailMultiAlternatives

logger = logging.getLogger("mysite.email")

RESEND_ENDPOINT = "https://api.resend.com/emails"

# Un formulario de contacto puede esperar unos segundos, pero no colgarse:
# el visitante ya recibió su respuesta y esto ocurre después.
TIMEOUT_SEGUNDOS = 10


class ResendEmailBackend(BaseEmailBackend):
    """Entrega los mensajes a través de la API de Resend.

    Se eligió Resend por tres razones concretas: 3.000 correos al mes en el
    plan gratuito —el formulario de un portafolio no se acerca ni de lejos—,
    una API de un solo endpoint, y un panel donde se ve si cada correo se
    entregó o rebotó. Eso último es lo que SMTP nunca da: con SMTP el envío
    "sale bien" y uno se entera del rebote cuando ya es tarde.
    """

    def __init__(self, fail_silently: bool = False, **kwargs) -> None:
        super().__init__(fail_silently=fail_silently)
        self.api_key = getattr(settings, "RESEND_API_KEY", "")

    def send_messages(self, email_messages: list[EmailMessage]) -> int:
        if not email_messages:
            return 0

        if not self.api_key:
            logger.error("RESEND_API_KEY no está configurada: no se envió ningún correo.")
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY no está configurada.")
            return 0

        enviados = 0
        for message in email_messages:
            if self._send_one(message):
                enviados += 1
        return enviados

    def _send_one(self, message: EmailMessage) -> bool:
        payload = {
            "from": message.from_email,
            "to": list(message.to),
            "subject": message.subject,
            "text": message.body,
        }
        if message.cc:
            payload["cc"] = list(message.cc)
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)

        # La versión en HTML viaja como "alternativa" en Django. Si existe,
        # se manda también: los clientes de correo prefieren el HTML y caen
        # al texto plano solos cuando no pueden mostrarlo.
        if isinstance(message, EmailMultiAlternatives):
            for contenido, tipo in message.alternatives:
                if tipo == "text/html":
                    payload["html"] = contenido
                    break

        try:
            response = requests.post(
                RESEND_ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=TIMEOUT_SEGUNDOS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            # Se registra el cuerpo de la respuesta porque los errores útiles
            # de Resend viajan ahí: dominio sin verificar, remitente no
            # autorizado, clave revocada. El código HTTP a secas no basta
            # para saber qué arreglar.
            detalle = getattr(exc.response, "text", "")[:300] if exc.response is not None else ""
            logger.error("Resend rechazó el envío: %s %s", exc, detalle)
            if not self.fail_silently:
                raise
            return False

        return True
