"""Limitación de peticiones y la exención del proceso de build.

Estas pruebas nacen de un fallo real detectado en integración: el build de
Astro hace ~22 peticiones en pocos segundos desde una sola IP y recibía **429**
de la propia API. En GitHub Actions habría roto todos los despliegues, y
ninguna prueba unitaria lo veía porque ninguna ejercitaba ese patrón.

⚠️ Trampa de DRF que descubrimos escribiendo esto: `SimpleRateThrottle` fija
`THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES` como **atributo de
clase, al importar el módulo**. `override_settings(REST_FRAMEWORK=...)` NO lo
alcanza: `api_settings` refleja el valor nuevo, pero el throttle sigue usando
el viejo. Para cambiar el límite en una prueba hay que parchear el atributo
de la clase, que es lo que hace la fixture `fast_limit`.
"""

import pytest
from django.core.cache import caches
from django.test import override_settings
from django.urls import reverse

from core.throttling import SharedAnonRateThrottle, is_build_request

pytestmark = pytest.mark.django_db

BUILD_TOKEN = "token-de-prueba-suficientemente-largo-para-comparar"


@pytest.fixture
def fast_limit(monkeypatch):
    """Baja el límite anónimo a 5/min para que la prueba sea rápida.

    Se parchea el atributo de clase, no los settings: ver la nota del módulo.
    """
    monkeypatch.setattr(
        SharedAnonRateThrottle,
        "THROTTLE_RATES",
        {**SharedAnonRateThrottle.THROTTLE_RATES, "anon": "5/min"},
    )
    caches["default"].clear()
    yield
    caches["default"].clear()


def _hammer(api_client, url, times, headers=None) -> dict[int, int]:
    """Lanza `times` peticiones y devuelve el recuento por código de estado."""
    codes: dict[int, int] = {}
    for _ in range(times):
        status = api_client.get(url, **(headers or {})).status_code
        codes[status] = codes.get(status, 0) + 1
    return codes


@override_settings(BUILD_API_TOKEN=BUILD_TOKEN)
def test_anonymous_requests_are_throttled(api_client, fast_limit):
    """Sin token, el límite se aplica: es la protección contra rastreadores."""
    codes = _hammer(api_client, reverse("v1:project-list"), 8)
    assert codes.get(200, 0) == 5
    assert codes.get(429, 0) == 3


@override_settings(BUILD_API_TOKEN=BUILD_TOKEN)
def test_build_token_bypasses_the_limit(api_client, fast_limit):
    """Con el token correcto, el build prerenderiza sin recibir 429.

    20 peticiones con un límite de 5/min: sin la exención, 15 serían 429 y el
    despliegue fallaría.
    """
    codes = _hammer(
        api_client,
        reverse("v1:project-list"),
        20,
        headers={"HTTP_X_BUILD_TOKEN": BUILD_TOKEN},
    )
    assert codes.get(429, 0) == 0, "el build sigue siendo limitado"
    assert codes.get(200, 0) == 20


@override_settings(BUILD_API_TOKEN=BUILD_TOKEN)
def test_wrong_token_gets_no_exemption(api_client, fast_limit):
    """Un token inventado no debe abrir ninguna puerta."""
    codes = _hammer(
        api_client,
        reverse("v1:project-list"),
        8,
        headers={"HTTP_X_BUILD_TOKEN": "token-incorrecto"},
    )
    assert codes.get(429, 0) == 3


class _Request:
    """Sustituto mínimo de HttpRequest: is_build_request solo mira META."""

    def __init__(self, token: str) -> None:
        self.META = {"HTTP_X_BUILD_TOKEN": token}


@override_settings(BUILD_API_TOKEN="")
def test_empty_setting_disables_the_exemption():
    """Con BUILD_API_TOKEN vacío, mandar la cabecera no exime de nada.

    Importa porque el valor por defecto ES vacío: una configuración
    incompleta no puede convertirse accidentalmente en una puerta abierta.
    """
    assert is_build_request(_Request("")) is False
    assert is_build_request(_Request("cualquier-cosa")) is False


@override_settings(BUILD_API_TOKEN=BUILD_TOKEN)
def test_only_the_exact_token_counts():
    assert is_build_request(_Request("")) is False
    assert is_build_request(_Request(BUILD_TOKEN[:-1])) is False
    assert is_build_request(_Request(BUILD_TOKEN)) is True
