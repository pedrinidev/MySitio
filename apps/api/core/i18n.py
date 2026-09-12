"""Resolución de contenido bilingüe.

El modelo guarda `titulo_es` y `titulo_en`; la API expone `titulo`. Toda la
traducción del sistema pasa por estas dos funciones, así que cambiar la
estrategia (añadir aymara, migrar a otra librería) se hace en un solo sitio.
"""

from __future__ import annotations

from django.conf import settings


def normalize_language(raw: str | None) -> str:
    """Devuelve un idioma soportado a partir de una entrada arbitraria.

    Una entrada inválida no es un error: se cae al idioma por defecto. Un
    visitante que manipule ?lang= debe ver el sitio en español, no un 400.
    """
    if not raw:
        return settings.DEFAULT_LANGUAGE
    code = raw.strip().lower()[:2]
    return code if code in settings.SUPPORTED_LANGUAGES else settings.DEFAULT_LANGUAGE


def translate(instance: object, field: str, language: str) -> str:
    """Lee `field_<language>` con degradación al idioma por defecto.

    Si la traducción al inglés está vacía se devuelve el español. Es preferible
    mostrar contenido en otro idioma que mostrar un hueco en blanco: el
    visitante entiende lo primero y desconfía de lo segundo.
    """
    value = getattr(instance, f"{field}_{language}", "") or ""
    if value:
        return value
    if language != settings.DEFAULT_LANGUAGE:
        return getattr(instance, f"{field}_{settings.DEFAULT_LANGUAGE}", "") or ""
    return ""
