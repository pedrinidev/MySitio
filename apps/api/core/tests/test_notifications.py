"""El canal de avisos del formulario de contacto.

Existe porque el canal ya cambió tres veces —SMTP, Resend, Telegram— y cada
cambio se hizo sobre un formulario que en producción es la única vía por la
que llega una oferta. Estas pruebas fijan lo que no puede romperse al
cambiarlo otra vez: que el aviso salga, que salga legible, y que un fallo no
escriba el token del bot en los registros.
"""

import logging

import pytest
import requests
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from core.notifications import (
    TELEGRAM_AVISO_RECORTE,
    TELEGRAM_MAX_CARACTERES,
    EmailNotifier,
    ErrorDeEntrega,
    Notification,
    TelegramNotifier,
    escapar_telegram,
    get_notifiers,
    send_notification,
)

TOKEN = "123456:AAEjemploDeTokenDeBot"

TELEGRAM = {
    "NOTIFY_CHANNELS": ["telegram"],
    "TELEGRAM_BOT_TOKEN": TOKEN,
    "TELEGRAM_CHAT_ID": "987",
}


def _aviso(text: str = "Hola Pedro, vimos tu portafolio.") -> Notification:
    return Notification(
        subject="[pedrinidev.com] Pasantía",
        title="Nuevo mensaje desde el portafolio",
        fields=(("Nombre", "Ana Reclutadora"), ("Correo", "ana@empresa.com")),
        text=text,
        reply_to="ana@empresa.com",
    )


# ──────────────────────── Selección de canal ──────────────────


@override_settings(**TELEGRAM)
def test_el_canal_configurado_es_el_que_se_usa():
    assert [type(n) for n in get_notifiers()] == [TelegramNotifier]


@override_settings(NOTIFY_CHANNELS=["email"])
def test_el_canal_de_correo_sigue_disponible():
    assert [type(n) for n in get_notifiers()] == [EmailNotifier]


@override_settings(NOTIFY_CHANNELS=["telegram", "email"])
def test_los_dos_canales_conviven_y_en_orden():
    assert [type(n) for n in get_notifiers()] == [TelegramNotifier, EmailNotifier]


@override_settings(NOTIFY_CHANNELS=["paloma-mensajera"])
def test_un_canal_inventado_falla_al_arrancar_y_no_en_silencio():
    """Lo peor que puede hacer un canal de avisos es no avisar sin decirlo."""
    with pytest.raises(ImproperlyConfigured) as error:
        get_notifiers()
    assert "paloma-mensajera" in str(error.value)


@override_settings(NOTIFY_CHANNELS=[])
def test_sin_ningun_canal_no_arranca():
    with pytest.raises(ImproperlyConfigured):
        send_notification(_aviso())


@override_settings(NOTIFY_CHANNELS=["telegram"], TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="")
def test_telegram_sin_credenciales_avisa_de_lo_que_falta():
    with pytest.raises(ImproperlyConfigured):
        send_notification(_aviso())


# ─────────────────────────── Entrega ──────────────────────────


@override_settings(**TELEGRAM)
def test_el_aviso_llega_con_los_datos_del_visitante(monkeypatch):
    llamadas = {}

    def _post(url, **kwargs):
        llamadas["url"] = url
        llamadas["json"] = kwargs["json"]
        return type("R", (), {"raise_for_status": lambda self: None})()

    monkeypatch.setattr("core.notifications.requests.post", _post)
    assert send_notification(_aviso()) is True

    assert llamadas["url"] == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    cuerpo = llamadas["json"]
    assert cuerpo["chat_id"] == "987"
    assert cuerpo["parse_mode"] == "HTML"
    assert cuerpo["disable_web_page_preview"] is True

    # Sin estos tres datos el aviso no sirve: no se sabe quién escribió,
    # ni a dónde responder, ni qué dijo.
    assert "Ana Reclutadora" in cuerpo["text"]
    assert "ana@empresa.com" in cuerpo["text"]
    assert "Hola Pedro, vimos tu portafolio." in cuerpo["text"]


# ───────────────────────── Maquetado ──────────────────────────


def test_se_escapan_las_etiquetas_que_romperian_el_analizador():
    assert escapar_telegram("<b>&</b>") == "&lt;b&gt;&amp;&lt;/b&gt;"


def test_las_comillas_y_apostrofos_se_dejan_como_estan():
    """`django.utils.html.escape` los convierte en &quot; y &#x27;, entidades
    que el analizador de Telegram no garantiza: llegarían literales en mitad
    del texto. Un mensaje con un apóstrofo no es un caso raro."""
    assert escapar_telegram('L\'entreprise dijo "sí"') == 'L\'entreprise dijo "sí"'


@override_settings(**TELEGRAM)
def test_un_mensaje_larguisimo_se_recorta_en_vez_de_ser_rechazado(monkeypatch):
    """Telegram no recorta lo que se pasa del tope: rechaza el mensaje
    entero. Como el formulario admite 5000 caracteres y el tope son 4096,
    el caso se alcanza escribiendo mucho — y perder ese aviso sería perder
    justo el mensaje más largo que alguien se molestó en escribir."""
    enviado = {}

    def _post(url, **kwargs):
        enviado["text"] = kwargs["json"]["text"]
        return type("R", (), {"raise_for_status": lambda self: None})()

    monkeypatch.setattr("core.notifications.requests.post", _post)
    send_notification(_aviso(text="a" * 5000))

    assert len(enviado["text"]) <= TELEGRAM_MAX_CARACTERES
    assert TELEGRAM_AVISO_RECORTE in enviado["text"]
    # Y lo que sí entra se manda, no se descarta el mensaje por largo.
    assert "aaaa" in enviado["text"]


# ──────────────────────────── Fallos ──────────────────────────


@override_settings(**TELEGRAM)
def test_un_fallo_propaga_para_que_el_llamante_decida(monkeypatch):
    """El notificador no se traga los errores: el módulo de contacto es
    quien decide que un fallo de aviso no debe romperle la respuesta al
    visitante, porque su mensaje ya está guardado."""
    monkeypatch.setattr(
        "core.notifications.requests.post",
        lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("caída")),
    )
    with pytest.raises(requests.RequestException):
        send_notification(_aviso())


@override_settings(**TELEGRAM)
def test_el_token_del_bot_nunca_llega_a_los_registros(monkeypatch, caplog):
    """El token va dentro de la URL y `requests` mete la URL en el texto de
    la excepción. Sin limpiarlo, un corte de red deja la credencial del bot
    escrita en unos registros que se leen, se copian y se pegan."""
    fallo = requests.ConnectionError(
        f"HTTPSConnectionPool: /bot{TOKEN}/sendMessage (Caused by NewConnectionError)"
    )
    monkeypatch.setattr(
        "core.notifications.requests.post", lambda *a, **k: (_ for _ in ()).throw(fallo)
    )

    # El logger «mysite» tiene propagate=False (ver LOGGING en base.py), así
    # que el handler que caplog pone en la raíz no lo alcanza: hay que
    # engancharlo al logger concreto o esta prueba pasaría en vacío.
    registro = logging.getLogger("mysite.notifications")
    registro.addHandler(caplog.handler)
    try:
        with pytest.raises(requests.RequestException):
            send_notification(_aviso())
    finally:
        registro.removeHandler(caplog.handler)

    assert TOKEN not in caplog.text
    assert "***" in caplog.text


def test_el_mensaje_no_queda_pegado_a_la_cabecera():
    """Sin la línea en blanco, lo que escribió el visitante se lee como si
    fuera un campo más de la ficha. Se coló una vez."""
    from core.notifications import componer_telegram

    texto = componer_telegram(_aviso(text="Lo que escribió el visitante."))
    assert "\n\nLo que escribió el visitante." in texto


# ────────────────────── Varios canales a la vez ───────────────

AMBOS = {
    "NOTIFY_CHANNELS": ["telegram", "email"],
    "TELEGRAM_BOT_TOKEN": TOKEN,
    "TELEGRAM_CHAT_ID": "987",
}


def _telegram_ok(monkeypatch, registro: dict):
    def _post(url, **kwargs):
        registro["text"] = kwargs["json"]["text"]
        return type("R", (), {"raise_for_status": lambda self: None})()

    monkeypatch.setattr("core.notifications.requests.post", _post)


def _telegram_caido(monkeypatch):
    monkeypatch.setattr(
        "core.notifications.requests.post",
        lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("caída")),
    )


@override_settings(**AMBOS)
def test_con_dos_canales_el_aviso_sale_por_los_dos(monkeypatch):
    from django.core import mail

    enviado = {}
    _telegram_ok(monkeypatch, enviado)

    assert send_notification(_aviso()) is True
    assert "Ana Reclutadora" in enviado["text"]
    assert len(mail.outbox) == 1


@override_settings(**AMBOS)
def test_si_telegram_cae_el_correo_salva_el_aviso(monkeypatch):
    """Es el motivo entero de tener dos canales. Si un canal caído dejara al
    otro sin enviar, tener dos sería peor que tener uno: se duplicaría la
    superficie de fallo sin ganar nada."""
    from django.core import mail

    _telegram_caido(monkeypatch)

    assert send_notification(_aviso()) is True
    assert len(mail.outbox) == 1


@override_settings(**AMBOS)
def test_si_caen_los_dos_si_se_entera_el_llamante(monkeypatch):
    """Solo cuando nadie recibe el aviso hay algo que reportar: ahí el
    mensaje queda marcado como no entregado para poder revisarlo."""
    _telegram_caido(monkeypatch)
    monkeypatch.setattr(
        "django.core.mail.EmailMultiAlternatives.send",
        lambda *a, **k: (_ for _ in ()).throw(OSError("correo caído")),
    )

    # Propaga el PRIMER fallo, el de Telegram: es el primero de la lista
    # y el que más información da sobre qué hay que arreglar.
    with pytest.raises(ErrorDeEntrega):
        send_notification(_aviso())


@override_settings(**AMBOS)
def test_el_canal_caido_queda_registrado_aunque_el_otro_entregue(monkeypatch, caplog):
    """Un canal roto durante semanas sin que nadie lo note es exactamente lo
    que pasó con SMTP. Si el otro entrega, el aviso llega igual y nada
    chirría: el registro es la única señal de que algo está mal."""
    _telegram_caido(monkeypatch)

    registro = logging.getLogger("mysite.notifications")
    registro.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.ERROR):
            send_notification(_aviso())
    finally:
        registro.removeHandler(caplog.handler)

    assert "TelegramNotifier" in caplog.text
