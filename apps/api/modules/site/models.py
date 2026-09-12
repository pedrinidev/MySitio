"""Identidad del portafolio.

Estos modelos son la fuente de verdad del apartado «Sobre mí» y del CV. Una
sola edición alimenta ambos: mantener el CV y la web sincronizados a mano es
un trabajo que siempre se acaba abandonando.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.markdown import render_markdown
from core.models import OrderedModel, TimeStampedModel, widen_update_fields


class Profile(TimeStampedModel):
    """Datos personales. Instancia única."""

    full_name = models.CharField(_("nombre completo"), max_length=120)
    role_es = models.CharField(_("rol (ES)"), max_length=160)
    role_en = models.CharField(_("rol (EN)"), max_length=160, blank=True)

    headline_es = models.CharField(
        _("titular (ES)"),
        max_length=255,
        help_text=_("Frase principal del hero. Corta y concreta."),
    )
    headline_en = models.CharField(_("titular (EN)"), max_length=255, blank=True)

    bio_es = models.TextField(_("biografía (ES)"), help_text=_("Markdown."))
    bio_en = models.TextField(_("biografía (EN)"), blank=True)
    bio_html_es = models.TextField(editable=False, blank=True)
    bio_html_en = models.TextField(editable=False, blank=True)

    email = models.EmailField(_("correo"))
    phone = models.CharField(_("teléfono"), max_length=32, blank=True)
    location_es = models.CharField(_("ubicación (ES)"), max_length=120)
    location_en = models.CharField(_("ubicación (EN)"), max_length=120, blank=True)
    availability_es = models.CharField(_("disponibilidad (ES)"), max_length=255, blank=True)
    availability_en = models.CharField(_("disponibilidad (EN)"), max_length=255, blank=True)

    avatar = models.ImageField(_("foto"), upload_to="profile/", blank=True)
    cv_es = models.FileField(_("CV en español"), upload_to="cv/", blank=True)
    cv_en = models.FileField(_("CV en inglés"), upload_to="cv/", blank=True)

    class Meta:
        verbose_name = _("perfil")
        verbose_name_plural = _("perfil")

    def __str__(self) -> str:
        return self.full_name

    def clean(self) -> None:
        # Barrera a nivel de modelo, no solo del admin: cualquier ruta de
        # creación (fixtures, shell, comando de carga) topa con la misma regla.
        if not self.pk and Profile.objects.exists():
            raise ValidationError(_("Ya existe un perfil. Editá el que hay en vez de crear otro."))

    def save(self, *args, **kwargs) -> None:
        self.bio_html_es = render_markdown(self.bio_es)
        self.bio_html_en = render_markdown(self.bio_en)
        widen_update_fields(kwargs, {"bio_html_es", "bio_html_en"})
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> Profile | None:
        """Devuelve el perfil, o None si aún no se creó."""
        return cls.objects.first()


class SocialLink(OrderedModel):
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="socials", verbose_name=_("perfil")
    )
    name = models.CharField(_("nombre"), max_length=40, help_text=_("GitHub, LinkedIn…"))
    url = models.URLField(_("enlace"))
    icon = models.CharField(
        _("icono"),
        max_length=40,
        help_text=_("Identificador del icono en el frontend: github, linkedin, mail…"),
    )

    class Meta(OrderedModel.Meta):
        verbose_name = _("enlace social")
        verbose_name_plural = _("enlaces sociales")

    def __str__(self) -> str:
        return self.name


class SkillGroup(OrderedModel):
    """Agrupación de tecnologías: Mobile, Backend, Bases de datos…"""

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="skill_groups", verbose_name=_("perfil")
    )
    name_es = models.CharField(_("nombre (ES)"), max_length=80)
    name_en = models.CharField(_("nombre (EN)"), max_length=80, blank=True)

    class Meta(OrderedModel.Meta):
        verbose_name = _("grupo de habilidades")
        verbose_name_plural = _("grupos de habilidades")

    def __str__(self) -> str:
        return self.name_es


class Skill(OrderedModel):
    group = models.ForeignKey(
        SkillGroup, on_delete=models.CASCADE, related_name="skills", verbose_name=_("grupo")
    )
    name = models.CharField(_("nombre"), max_length=60)
    level = models.PositiveSmallIntegerField(
        _("nivel"),
        default=3,
        choices=[(1, "1 · Básico"), (2, "2"), (3, "3 · Sólido"), (4, "4"), (5, "5 · Avanzado")],
    )
    is_primary = models.BooleanField(
        _("destacada"),
        default=False,
        help_text=_("Las destacadas aparecen en el resumen del hero."),
    )

    class Meta(OrderedModel.Meta):
        verbose_name = _("habilidad")
        verbose_name_plural = _("habilidades")

    def __str__(self) -> str:
        return self.name


class ExperienceItem(OrderedModel):
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="experience", verbose_name=_("perfil")
    )
    role_es = models.CharField(_("puesto (ES)"), max_length=160)
    role_en = models.CharField(_("puesto (EN)"), max_length=160, blank=True)
    organization = models.CharField(_("organización"), max_length=160)
    start_date = models.DateField(_("desde"))
    end_date = models.DateField(_("hasta"), null=True, blank=True, help_text=_("Vacío = actual."))
    description_es = models.TextField(_("descripción (ES)"), blank=True)
    description_en = models.TextField(_("descripción (EN)"), blank=True)
    highlights_es = models.TextField(
        _("aportes (ES)"),
        blank=True,
        help_text=_("Un aporte por línea."),
    )
    highlights_en = models.TextField(_("aportes (EN)"), blank=True)

    class Meta:
        ordering = ("-start_date", "order")
        verbose_name = _("experiencia")
        verbose_name_plural = _("experiencia")

    def __str__(self) -> str:
        return f"{self.role_es} — {self.organization}"

    def clean(self) -> None:
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": _("La fecha de fin no puede ser anterior al inicio.")}
            )

    @property
    def is_current(self) -> bool:
        return self.end_date is None
