"""La API pública no debe romperse por tener sesión de administrador.

Este fallo llegó a producción y era especialmente traicionero: solo lo
sufría quien tuviera la sesión del admin abierta —o sea, el dueño del
sitio— mientras que para cualquier visitante funcionaba bien. El síntoma
era un 403 al enviar el formulario de contacto.

La causa: DRF aplica SessionAuthentication por defecto, y esa clase exige
un token CSRF en cuanto la petición trae cookie de sesión.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

PAYLOAD = {
    "name": "Alguien",
    "email": "alguien@ejemplo.com",
    "subject": "Consulta de prueba",
    "message": "Mensaje suficientemente largo para pasar la validacion.",
    "website": "",
    "elapsed_ms": 9000,
}


@pytest.mark.django_db
def test_contacto_funciona_con_sesion_de_admin_abierta():
    """El caso exacto que fallaba en producción.

    `enforce_csrf_checks=True` NO es opcional aquí. El cliente de pruebas de
    Django desactiva la comprobación CSRF por defecto, así que sin esta
    bandera la prueba pasaba con el código roto y no servía de nada.
    """
    admin = get_user_model().objects.create_superuser(
        username="admin-prueba", email="a@ejemplo.com", password="clave-larga-de-prueba"
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(admin)

    response = client.post("/api/v1/contact/", PAYLOAD, content_type="application/json")

    assert response.status_code == 201, (
        f"Con sesión de admin devolvió {response.status_code}. "
        "Si es 403, volvió SessionAuthentication a los ajustes de DRF."
    )


@pytest.mark.django_db
def test_contacto_sigue_funcionando_sin_sesion():
    """El caso normal, que nunca falló, para no arreglar uno rompiendo el otro."""
    client = Client(enforce_csrf_checks=True)
    response = client.post("/api/v1/contact/", PAYLOAD, content_type="application/json")
    assert response.status_code == 201
