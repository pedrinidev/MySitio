"""Piezas reutilizables del panel de administración.

El admin es la herramienta que Pedro va a usar todas las semanas. Merece el
mismo cuidado que la parte pública: si publicar un post es incómodo, no se
publican posts.
"""

from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse


class TimeStampedAdminMixin:
    """Muestra las marcas de tiempo como solo lectura."""

    readonly_fields = ("created_at", "updated_at")


class SingletonAdminMixin:
    """Admin para modelos de instancia única (por ejemplo, el perfil).

    Impide crear un segundo registro y lleva directo al formulario de edición
    en vez de a un listado de un solo elemento.
    """

    def has_add_permission(self, request: HttpRequest) -> bool:
        return not self.model.objects.exists()

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def changelist_view(self, request: HttpRequest, extra_context=None):
        instance = self.model.objects.first()
        opts = self.model._meta
        if instance is not None:
            return HttpResponseRedirect(
                reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[instance.pk])
            )
        return HttpResponseRedirect(reverse(f"admin:{opts.app_label}_{opts.model_name}_add"))


@admin.display(description="Idiomas")
def translation_status(obj, fields: tuple[str, ...]) -> str:
    """Resume qué traducciones están completas.

    Ver de un vistazo qué le falta al inglés evita publicar medio sitio a
    medias — el fallo más frecuente en un sitio bilingüe mantenido por una
    sola persona.
    """
    missing = [f for f in fields if not getattr(obj, f"{f}_en", "")]
    return "ES · EN" if not missing else f"ES · falta EN ({', '.join(missing)})"
