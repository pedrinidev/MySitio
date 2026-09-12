"""El healthcheck local no debe chocar con ALLOWED_HOSTS.

Este fallo llegó hasta producción: el despliegue comprobaba la salud
pidiendo a 127.0.0.1 y Django devolvía 400. El ensayo local no lo detectó
porque allí ALLOWED_HOSTS incluía la loopback — un ensayo más permisivo que
la realidad no prueba nada. De ahí estas tres pruebas.
"""

import pytest
from django.test import override_settings

HEALTH = "/api/v1/health/"


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["pedrinidev.com"])
def test_healthcheck_desde_loopback_funciona(client):
    """Es el caso real: Docker y el despliegue piden a 127.0.0.1."""
    response = client.get(HEALTH, HTTP_HOST="127.0.0.1:8000", REMOTE_ADDR="127.0.0.1")
    assert response.status_code == 200


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["pedrinidev.com"])
def test_host_invalido_desde_fuera_sigue_rechazado(client):
    """La excepción NO puede servir para saltarse la validación.

    Nginx reenvía el Host del cliente, así que si esto pasara, cualquiera
    desde internet podría presentarse como 127.0.0.1.
    """
    response = client.get(HEALTH, HTTP_HOST="127.0.0.1:8000", REMOTE_ADDR="198.51.100.7")
    assert response.status_code == 400


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["pedrinidev.com"])
def test_otra_ruta_desde_loopback_sigue_rechazada(client):
    """La excepción se limita a la ruta de salud, no a todo lo local."""
    response = client.get("/api/v1/projects/", HTTP_HOST="127.0.0.1:8000", REMOTE_ADDR="127.0.0.1")
    assert response.status_code == 400
