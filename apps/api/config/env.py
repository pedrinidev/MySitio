"""Lectura tipada de variables de entorno.

Se implementa a mano en lugar de añadir django-environ: son sesenta líneas,
una dependencia menos que auditar y control total sobre los mensajes de error.

Regla central: en producción, una variable obligatoria que falta debe hacer
que el proceso **no arranque**. Un servidor que se levanta con la mitad de su
configuración es mucho peor que uno que no se levanta.
"""

from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

_TRUE_VALUES = frozenset({"1", "true", "yes", "on", "si", "sí"})


class _Missing:
    """Centinela para distinguir «sin valor por defecto» de «por defecto None»."""


_MISSING = _Missing()


def env(name: str, default: object = _MISSING) -> str:
    """Devuelve una variable de entorno como texto.

    Raises:
        ImproperlyConfigured: si no existe y no se indicó valor por defecto.
    """
    value = os.environ.get(name)
    if value is None or value == "":
        if isinstance(default, _Missing):
            raise ImproperlyConfigured(
                f"Falta la variable de entorno obligatoria: {name}. "
                f"Revisá .env.example para ver qué se espera."
            )
        return default  # type: ignore[return-value]
    return value


def env_bool(name: str, default: bool = False) -> bool:
    """Interpreta una variable como booleano ('1', 'true', 'yes', 'on', 'si')."""
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in _TRUE_VALUES


def env_int(name: str, default: int | None = None) -> int:
    """Interpreta una variable como entero."""
    raw = os.environ.get(name)
    if raw is None or raw == "":
        if default is None:
            raise ImproperlyConfigured(f"Falta la variable de entorno obligatoria: {name}")
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"{name} debe ser un número entero, se recibió: {raw!r}"
        ) from exc


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    """Interpreta una variable como lista separada por comas, sin elementos vacíos."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return list(default or [])
    return [item.strip() for item in raw.split(",") if item.strip()]
