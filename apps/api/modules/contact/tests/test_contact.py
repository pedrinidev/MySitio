"""El formulario de contacto: la única vía por la que llega una oferta."""

import pytest
from django.core import mail
from django.urls import reverse

from modules.contact.models import ContactMessage, MessageStatus

pytestmark = pytest.mark.django_db

VALID = {
    "name": "Ana Reclutadora",
    "email": "ana@empresa.com",
    "subject": "Pasantía",
    "message": "Hola Pedro, vimos tu portafolio y queremos conversar contigo.",
    "locale": "es",
    "website": "",
    "elapsed_ms": 25_000,
}


def test_valid_message_is_stored_and_emailed(api_client):
    response = api_client.post(reverse("v1:contact-create"), VALID, format="json")
    assert response.status_code == 201

    message = ContactMessage.objects.get()
    assert message.status == MessageStatus.NEW
    assert message.delivered is True
    assert len(mail.outbox) == 1
    # Responder en el cliente de correo debe escribir al visitante.
    assert mail.outbox[0].reply_to == ["ana@empresa.com"]


def test_honeypot_submission_is_flagged_but_still_answered_201(api_client):
    """Al bot se le responde igual que a un humano: no se le dice qué lo delató."""
    response = api_client.post(
        reverse("v1:contact-create"), {**VALID, "website": "http://spam.example"}, format="json"
    )
    assert response.status_code == 201
    assert ContactMessage.objects.get().status == MessageStatus.SPAM
    assert len(mail.outbox) == 0


def test_submission_faster_than_a_human_is_flagged(api_client):
    response = api_client.post(
        reverse("v1:contact-create"), {**VALID, "elapsed_ms": 400}, format="json"
    )
    assert response.status_code == 201
    assert ContactMessage.objects.get().status == MessageStatus.SPAM


def test_link_farm_is_rejected(api_client):
    response = api_client.post(
        reverse("v1:contact-create"),
        {**VALID, "message": "compra " + " ".join(["http://spam.example"] * 8)},
        format="json",
    )
    assert response.status_code == 400


def test_ip_is_never_stored_in_clear(api_client):
    api_client.post(
        reverse("v1:contact-create"), VALID, format="json", HTTP_X_REAL_IP="190.104.22.10"
    )
    message = ContactMessage.objects.get()
    assert "190.104" not in message.ip_hash
    assert len(message.ip_hash) == 64


def test_message_survives_smtp_failure(api_client, monkeypatch):
    """Perder el mensaje de un reclutador por un timeout de SMTP es inaceptable."""

    def _boom(*args, **kwargs):
        raise OSError("SMTP caído")

    monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", _boom)

    response = api_client.post(reverse("v1:contact-create"), VALID, format="json")
    assert response.status_code == 201  # el visitante no ve el fallo

    message = ContactMessage.objects.get()
    assert message.delivered is False  # pero queda registrado para revisarlo


def test_el_aviso_por_telegram_recorre_la_cadena_entera(api_client, monkeypatch, settings):
    """Del formulario al aviso, sin saltarse ningún eslabón.

    Las pruebas de `core/notifications.py` comprueban el canal por separado
    y las de aquí arriba comprueban el formulario con el canal de correo.
    Entre medias queda la costura —vista, servicio, notificador— que es
    justo donde se rompió dos veces.
    """
    settings.NOTIFY_CHANNELS = ["telegram"]
    settings.TELEGRAM_BOT_TOKEN = "123:ABC"
    settings.TELEGRAM_CHAT_ID = "987"

    enviado = {}

    def _post(url, **kwargs):
        enviado.update(kwargs["json"])
        return type("R", (), {"raise_for_status": lambda self: None})()

    monkeypatch.setattr("core.notifications.requests.post", _post)

    response = api_client.post(reverse("v1:contact-create"), VALID, format="json")
    assert response.status_code == 201

    assert enviado["chat_id"] == "987"
    assert "Ana Reclutadora" in enviado["text"]
    assert "ana@empresa.com" in enviado["text"]
    assert "queremos conversar contigo" in enviado["text"]

    # Y queda constancia de que el aviso salió, no solo de que se guardó.
    assert ContactMessage.objects.get().delivered is True


def test_un_bot_no_gasta_un_aviso(api_client, monkeypatch, settings):
    """El spam se guarda para poder reclasificarlo, pero no suena el teléfono."""
    settings.NOTIFY_CHANNELS = ["telegram"]
    settings.TELEGRAM_BOT_TOKEN = "123:ABC"
    settings.TELEGRAM_CHAT_ID = "987"

    def _no_deberia_llamarse(*args, **kwargs):
        raise AssertionError("Un mensaje marcado como spam no debe avisar.")

    monkeypatch.setattr("core.notifications.requests.post", _no_deberia_llamarse)

    response = api_client.post(
        reverse("v1:contact-create"), {**VALID, "website": "http://spam.example"}, format="json"
    )
    assert response.status_code == 201
    assert ContactMessage.objects.get().status == MessageStatus.SPAM
