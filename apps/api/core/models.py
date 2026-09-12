"""Modelos abstractos compartidos por todos los módulos."""

from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """Añade marcas de creación y última modificación.

    Saber cuándo se tocó una fila por última vez cuesta dos columnas y ahorra
    horas cuando hay que depurar en producción.
    """

    created_at = models.DateTimeField(_("creado"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("actualizado"), auto_now=True)

    class Meta:
        abstract = True


class PublicationStatus(models.TextChoices):
    DRAFT = "draft", _("Borrador")
    PUBLISHED = "published", _("Publicado")


class PublishableQuerySet(models.QuerySet):
    """Consultas reutilizables para cualquier contenido publicable."""

    def published(self) -> PublishableQuerySet:
        return self.filter(status=PublicationStatus.PUBLISHED)

    def drafts(self) -> PublishableQuerySet:
        return self.filter(status=PublicationStatus.DRAFT)


class PublishableModel(models.Model):
    """Contenido con ciclo de vida borrador → publicado.

    El estado por defecto es BORRADOR. Que algo se publique tiene que ser un
    acto deliberado, nunca un descuido.
    """

    status = models.CharField(
        _("estado"),
        max_length=16,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
        db_index=True,
    )

    objects = PublishableQuerySet.as_manager()

    class Meta:
        abstract = True

    @property
    def is_published(self) -> bool:
        return self.status == PublicationStatus.PUBLISHED


class OrderedModel(models.Model):
    """Orden manual controlado desde el admin."""

    order = models.PositiveIntegerField(_("orden"), default=0, db_index=True)

    class Meta:
        abstract = True
        ordering = ("order",)


def default_published_at() -> timezone.datetime:
    return timezone.now()


def widen_update_fields(kwargs: dict, derived: set[str]) -> None:
    """Añade los campos derivados a `update_fields` si viene acotado.

    Django pasa `update_fields` cuando conoce qué cambió — y `update_or_create`
    lo hace SIEMPRE que el objeto ya existía. En ese caso `save()` recalcula el
    HTML a partir del Markdown y acto seguido lo descarta, porque el campo
    derivado no estaba en la lista: la base se queda con la versión anterior.

    El fallo es silencioso y difícil de ver: el Markdown queda bien guardado,
    así que en el Admin todo parece correcto, y lo que el sitio publica es el
    HTML viejo. Apareció al cambiar un texto con `seed_content` y ver que la
    página seguía mostrando la frase antigua.
    """
    fields = kwargs.get("update_fields")
    if fields is not None:
        kwargs["update_fields"] = set(fields) | derived
