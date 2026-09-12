"""El backend de correo por API HTTPS.

Existe porque DigitalOcean bloquea los puertos de SMTP en sus droplets: el
envío se quedaba en `timed out` y el mensaje, aunque guardado, nunca
notificaba. Estas pruebas fijan el contrato con la API de Resend para que un
cambio futuro no vuelva a dejar el formulario mudo en silencio.
"""

from unittest.mock import patch

import pytest
from django.core.mail import EmailMultiAlternatives
from django.test import override_settings

from core.email import ResendEmailBackend


def _mensaje() -> EmailMultiAlternatives:
    correo = EmailMultiAlternatives(
        subject="[pedrinidev.com] Consulta",
        body="Texto plano del mensaje.",
        from_email="contacto@pedrinidev.com",
        to=["pedrinidevs@gmail.com"],
        reply_to=["visitante@ejemplo.com"],
    )
    correo.attach_alternative("<p>Versión en HTML</p>", "text/html")
    return correo


@override_settings(RESEND_API_KEY="clave-de-prueba")
def test_envia_texto_y_html_a_la_api():
    with patch("core.email.requests.post") as post:
        post.return_value.raise_for_status.return_value = None
        enviados = ResendEmailBackend().send_messages([_mensaje()])

    assert enviados == 1
    cuerpo = post.call_args.kwargs["json"]
    assert cuerpo["from"] == "contacto@pedrinidev.com"
    assert cuerpo["to"] == ["pedrinidevs@gmail.com"]
    assert cuerpo["text"] == "Texto plano del mensaje."
    assert cuerpo["html"] == "<p>Versión en HTML</p>"
    # Sin reply_to, responder al aviso escribiría a la propia cuenta del
    # sitio en vez de a quien mandó el formulario.
    assert cuerpo["reply_to"] == ["visitante@ejemplo.com"]
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer clave-de-prueba"


@override_settings(RESEND_API_KEY="")
def test_sin_clave_no_revienta_si_se_pide_silencio():
    """El módulo de contacto llama con fail_silently: un fallo de correo no
    debe convertirse en un error de cara al visitante, cuyo mensaje ya está
    guardado."""
    assert ResendEmailBackend(fail_silently=True).send_messages([_mensaje()]) == 0


@override_settings(RESEND_API_KEY="")
def test_sin_clave_avisa_cuando_no_se_pide_silencio():
    with pytest.raises(ValueError):
        ResendEmailBackend(fail_silently=False).send_messages([_mensaje()])


@override_settings(RESEND_API_KEY="clave-de-prueba")
def test_un_fallo_de_red_no_propaga_con_silencio():
    import requests

    with patch("core.email.requests.post", side_effect=requests.ConnectionError("caida")):
        assert ResendEmailBackend(fail_silently=True).send_messages([_mensaje()]) == 0
