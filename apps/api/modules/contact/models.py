from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class MessageStatus(models.TextChoices):
    NEW = "new", _("Nuevo")
    READ = "read", _("Leído")
    REPLIED = "replied", _("Respondido")
    SPAM = "spam", _("Spam")


class ContactMessage(TimeStampedModel):
    """Mensaje del formulario de contacto.

    Se guarda SIEMPRE, incluso si el aviso no llega a salir. Perder el
    mensaje de un reclutador por un fallo de red no es aceptable.
    """

    name = models.CharField(_("nombre"), max_length=120)
    email = models.EmailField(_("correo"))
    subject = models.CharField(_("asunto"), max_length=200)
    message = models.TextField(_("mensaje"), max_length=5000)
    locale = models.CharField(_("idioma"), max_length=5, default="es")

    status = models.CharField(
        _("estado"),
        max_length=10,
        choices=MessageStatus.choices,
        default=MessageStatus.NEW,
        db_index=True,
    )
    delivered = models.BooleanField(
        _("avisado"),
        default=False,
        help_text=_("Sin marcar: el mensaje se guardó, pero el aviso no se pudo entregar."),
    )

    ip_hash = models.CharField(max_length=64, editable=False, db_index=True)
    user_agent = models.CharField(max_length=300, blank=True, editable=False)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("mensaje")
        verbose_name_plural = _("mensajes")

    def __str__(self) -> str:
        return f"{self.name} — {self.subject[:40]}"
