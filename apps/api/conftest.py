"""Configuración compartida de pytest."""

import pytest


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture(autouse=True)
def _clear_caches(request):
    """Limpia las cachés entre pruebas.

    Sin esto, el throttling y los tokens de un solo uso arrastran estado de una
    prueba a la siguiente y los fallos aparecen según el orden de ejecución —
    el peor tipo de test inestable.

    La caché `throttle` está respaldada por la base de datos, así que solo se
    limpia en pruebas que declaran acceso a base. Limpiarla siempre haría
    fallar cualquier prueba unitaria pura con un error de acceso a la base.
    """
    from django.core.cache import caches

    needs_db = "django_db" in request.keywords or "db" in request.fixturenames
    names = ["default", "throttle"] if needs_db else ["default"]

    def _clear() -> None:
        for name in names:
            caches[name].clear()

    _clear()
    yield
    _clear()
