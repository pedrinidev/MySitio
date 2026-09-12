"""Mixins de vista compartidos."""

from __future__ import annotations

from core.i18n import normalize_language


class LanguageMixin:
    """Inyecta el idioma pedido en el contexto del serializador.

    Se resuelve una sola vez por petición y viaja por contexto, de modo que
    ningún serializador tiene que leer `request.query_params` por su cuenta.
    """

    def get_language(self) -> str:
        return normalize_language(self.request.query_params.get("lang"))

    def get_serializer_context(self) -> dict:
        return {**super().get_serializer_context(), "lang": self.get_language()}
