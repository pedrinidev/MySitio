"""Aviso al dueño del sitio cuando llega un mensaje de contacto.

Por qué existe una capa propia en vez de llamar a ``EmailMessage.send()``
desde el módulo de contacto:

El canal de aviso cambió tres veces. Primero fue SMTP por Zoho, que murió
contra el bloqueo de puertos de DigitalOcean. Después la API de Resend, que
funciona pero obliga a verificar el dominio. Y finalmente Telegram, que no
pide dominio, ni registros DNS, ni cuenta de correo transaccional, y además
avisa en el teléfono en lugar de en una bandeja que se revisa cada tres
días. Cada uno de esos cambios tocaba el módulo de contacto, que no tiene
por qué enterarse de nada de esto.

El reparto queda así: el módulo de contacto decide **qué se dice**, este
módulo decide **cómo se entrega**. Sumar un canal nuevo es escribir una
clase y añadir una línea a ``CANALES``; el formulario no cambia.

Los canales son **varios a la vez**, no uno: ``NOTIFY_CHANNELS`` acepta una
lista y el aviso sale por todos. Que uno falle no deja al resto sin enviar,
porque la gracia de tener dos es justamente que no dependan el uno del
otro.

Por eso ``Notification`` viaja como datos estructurados y no como texto ya
maquetado. Es lo que permite que cada canal lo pinte a su manera: el correo
en HTML completo, y Telegram con el subconjunto de etiquetas que acepta su
API — que no incluye ``<h2>``, ``<p>`` ni ``<hr>``, así que reutilizar el
HTML del correo habría llegado como un amasijo de etiquetas literales.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

logger = logging.getLogger("mysite.notifications")

# El visitante ya recibió su respuesta cuando esto ocurre, así que puede
# tardar unos segundos. Lo que no puede es colgar un hilo de Gunicorn.
TIMEOUT_SEGUNDOS = 10

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Límite duro de la API de Telegram para un mensaje de texto.
TELEGRAM_MAX_CARACTERES = 4096
TELEGRAM_AVISO_RECORTE = "\n\n[…mensaje recortado, completo en el panel]"


class ErrorDeEntrega(requests.RequestException):
    """Fallo de entrega con el mensaje ya limpio de credenciales.

    Hereda de ``RequestException`` para que quien la capture no tenga que
    distinguirla de un fallo de red normal. Existe porque el texto de las
    excepciones de `requests` incluye la URL, y en Telegram el token va
    DENTRO de la URL: propagar la original hace que cualquiera que la
    registre —incluido el bucle de `send_notification`— escriba la
    credencial en los registros sin saberlo. Pasó, y lo cazó una prueba.
    """


@dataclass(frozen=True)
class Notification:
    """Un aviso, sin decidir todavía por dónde se manda.

    ``subject`` solo lo usa el correo; Telegram no tiene asunto. ``fields``
    son pares etiqueta/valor para la cabecera, y ``text`` el cuerpo libre.
    """

    subject: str
    title: str
    fields: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    text: str = ""
    reply_to: str = ""


class Notifier(ABC):
    """Un canal de entrega.

    Lanza si la entrega falla — no devuelve ``False`` en silencio. Quien
    llama decide si eso debe romper la petición; en el formulario de
    contacto no debe, porque el mensaje ya está guardado.
    """

    @abstractmethod
    def send(self, notification: Notification) -> bool: ...


# ──────────────────────────── Correo ──────────────────────────


class EmailNotifier(Notifier):
    """Entrega por correo, con el backend que diga ``EMAIL_BACKEND``.

    Sigue disponible a propósito aunque el canal por defecto sea Telegram:
    es el que produce un aviso presentable si algún día hace falta
    reenviarlo a alguien más.
    """

    def send(self, notification: Notification) -> bool:
        correo = EmailMultiAlternatives(
            subject=notification.subject,
            body=self._texto(notification),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.CONTACT_TO_EMAIL],
            # Responder en el cliente de correo escribe directamente al
            # visitante, sin copiar la dirección a mano.
            reply_to=[notification.reply_to] if notification.reply_to else None,
        )
        correo.attach_alternative(self._html(notification), "text/html")
        correo.send(fail_silently=False)
        return True

    @staticmethod
    def _texto(notification: Notification) -> str:
        regla = "-" * 40
        cabecera = "\n".join(f"{etiqueta}: {valor}" for etiqueta, valor in notification.fields)
        return f"{notification.title}\n{regla}\n{cabecera}\n{regla}\n\n{notification.text}\n"

    @staticmethod
    def _html(notification: Notification) -> str:
        cabecera = "<br>".join(
            f"<b>{escape(etiqueta)}:</b> {escape(valor)}" for etiqueta, valor in notification.fields
        )
        return (
            f"<h2>{escape(notification.title)}</h2>"
            f"<p>{cabecera}</p>"
            f"<hr><p style='white-space:pre-wrap'>{escape(notification.text)}</p>"
        )


# ─────────────────────────── Telegram ─────────────────────────


def escapar_telegram(texto: str) -> str:
    """Escapa para el ``parse_mode=HTML`` de Telegram.

    No se usa ``django.utils.html.escape`` porque convierte comillas y
    apóstrofos en ``&quot;`` y ``&#x27;``, y el analizador de Telegram solo
    garantiza las tres entidades de abajo: el resto llega literal y se lee
    como basura en mitad del texto. Un mensaje con un apóstrofo es de lo más
    normal, así que esto no es un caso raro.
    """
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def componer_telegram(notification: Notification) -> str:
    """Arma el mensaje respetando el tope de caracteres de la API.

    Un mensaje que pase de 4096 no se recorta: Telegram lo **rechaza
    entero**. Como el formulario admite hasta 5000 caracteres, el caso es
    alcanzable y hay que recortar aquí — con un aviso, para que se sepa que
    falta texto y dónde está el resto.
    """
    lineas = [f"<b>{escapar_telegram(notification.title)}</b>", ""]
    lineas += [
        f"<b>{escapar_telegram(etiqueta)}:</b> {escapar_telegram(valor)}"
        for etiqueta, valor in notification.fields
    ]
    # El "\n\n" del final separa la cabecera del mensaje: sin esa línea en
    # blanco el texto del visitante queda pegado al último campo y se lee
    # como si fuera parte de la ficha.
    prefijo = "\n".join(lineas) + "\n\n"

    disponible = TELEGRAM_MAX_CARACTERES - len(prefijo) - len(TELEGRAM_AVISO_RECORTE)
    cuerpo = escapar_telegram(notification.text)
    if len(cuerpo) > disponible:
        cuerpo = cuerpo[: max(disponible, 0)] + TELEGRAM_AVISO_RECORTE

    # Red de seguridad: si la cabecera sola ya desbordara, el recorte de
    # arriba no bastaría y la API devolvería 400.
    return (prefijo + cuerpo)[:TELEGRAM_MAX_CARACTERES]


class TelegramNotifier(Notifier):
    """Entrega por la API de bots de Telegram.

    Va por HTTPS al 443, así que atraviesa el bloqueo de puertos de correo
    de DigitalOcean igual que la API de Resend, pero sin cuenta de correo
    transaccional ni dominio verificado por medio.
    """

    def __init__(self) -> None:
        self.token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        self.chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")

    def send(self, notification: Notification) -> bool:
        if not self.token or not self.chat_id:
            raise ImproperlyConfigured(
                "TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID son obligatorios con el canal de Telegram."
            )

        try:
            response = requests.post(
                TELEGRAM_API.format(token=self.token),
                json={
                    "chat_id": self.chat_id,
                    "text": componer_telegram(notification),
                    "parse_mode": "HTML",
                    # El aviso lleva el correo del visitante: sin esto,
                    # Telegram intentaría pintar una tarjeta de vista previa.
                    "disable_web_page_preview": True,
                },
                timeout=TIMEOUT_SEGUNDOS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            # El token va DENTRO de la URL, y `requests` mete la URL en el
            # texto de la excepción. Sin este reemplazo, un fallo de red
            # escribiría el token del bot en los registros — que se leen,
            # se copian y se pegan en informes.
            seguro = str(exc).replace(self.token, "***") if self.token else str(exc)
            # El detalle útil viaja en el cuerpo (`description`), no en el
            # código HTTP: «chat not found», «bot was blocked by the user».
            detalle = getattr(exc.response, "text", "")[:300] if exc.response is not None else ""
            logger.error("Telegram rechazó el aviso: %s %s", seguro, detalle)
            # `from None` corta el encadenamiento a propósito: con `from exc`
            # la original viajaría en __cause__ y volvería a imprimirse —con
            # el token— en cuanto alguien registrara la traza completa.
            raise ErrorDeEntrega(seguro) from None

        return True


# ────────────────────────── Selección ─────────────────────────

CANALES: dict[str, type[Notifier]] = {
    "email": EmailNotifier,
    "telegram": TelegramNotifier,
}


def get_notifiers() -> list[Notifier]:
    """Instancia los canales de ``NOTIFY_CHANNELS``, en orden."""
    canales = getattr(settings, "NOTIFY_CHANNELS", ["email"])
    notificadores = []
    for canal in canales:
        try:
            notificadores.append(CANALES[canal]())
        except KeyError:
            raise ImproperlyConfigured(
                f"NOTIFY_CHANNELS incluye «{canal}», que no existe. "
                f"Opciones: {', '.join(sorted(CANALES))}."
            ) from None
    return notificadores


def send_notification(notification: Notification) -> bool:
    """Entrega por **todos** los canales configurados.

    Un canal que falla no impide los demás, y por eso el resultado no es un
    simple «salió bien»: si Telegram entrega y el correo rebota, el aviso
    llegó igual. Se considera entregado con que **uno** lo consiga, y solo
    se lanza cuando fallan todos — que es el único caso en el que nadie se
    entera del mensaje.

    El fallo de cada canal se registra por separado. Un canal caído durante
    semanas sin que nadie lo note es lo que ya pasó con SMTP.
    """
    notificadores = get_notifiers()
    if not notificadores:
        raise ImproperlyConfigured(
            "NOTIFY_CHANNELS está vacío: el formulario guardaría los mensajes "
            "sin avisar de ninguno."
        )

    entregados = 0
    fallos: list[Exception] = []

    for notificador in notificadores:
        nombre = type(notificador).__name__
        try:
            notificador.send(notification)
        except Exception as exc:
            logger.error("El canal %s no pudo entregar el aviso: %s", nombre, exc)
            fallos.append(exc)
        else:
            entregados += 1
            logger.info("Aviso entregado por %s", nombre)

    if entregados == 0:
        raise fallos[0]

    return True
