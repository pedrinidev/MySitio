"""Proyectos del portafolio: MentePro, ManiPDF, ManiFarm y los que vengan."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.markdown import render_markdown
from core.models import (
    OrderedModel,
    PublishableModel,
    PublishableQuerySet,
    TimeStampedModel,
    widen_update_fields,
)
from core.webhooks import schedule_site_rebuild


class TechnologyCategory(models.TextChoices):
    MOBILE = "mobile", _("Mobile")
    BACKEND = "backend", _("Backend")
    FRONTEND = "frontend", _("Frontend")
    DEVOPS = "devops", _("DevOps")
    DATABASE = "database", _("Bases de datos")
    DESIGN = "design", _("Diseño")


class Technology(OrderedModel):
    name = models.CharField(_("nombre"), max_length=60, unique=True)
    slug = models.SlugField(_("slug"), max_length=60, unique=True)
    category = models.CharField(
        _("categoría"),
        max_length=20,
        choices=TechnologyCategory.choices,
        default=TechnologyCategory.BACKEND,
        db_index=True,
    )
    color = models.CharField(
        _("color"),
        max_length=7,
        default="#6366f1",
        help_text=_("Hexadecimal, por ejemplo #7F52FF para Kotlin."),
    )
    icon = models.CharField(_("icono"), max_length=60, blank=True)

    class Meta(OrderedModel.Meta):
        verbose_name = _("tecnología")
        verbose_name_plural = _("tecnologías")

    def __str__(self) -> str:
        return self.name


class ProjectQuerySet(PublishableQuerySet):
    def with_related(self) -> ProjectQuerySet:
        """Precarga lo que el serializador siempre necesita.

        El listado de proyectos serializa las tecnologías de cada uno. Sin este
        prefetch son N+1 consultas; con él, dos.
        """
        return self.prefetch_related("technologies")

    def featured(self) -> ProjectQuerySet:
        return self.filter(featured=True)

    def by_technologies(self, slugs: list[str]) -> ProjectQuerySet:
        """Proyectos que usen CUALQUIERA de las tecnologías indicadas.

        `distinct()` es obligatorio: un proyecto con dos de las tecnologías
        filtradas aparecería duplicado por el JOIN.
        """
        if not slugs:
            return self
        return self.filter(technologies__slug__in=slugs).distinct()


class Project(TimeStampedModel, PublishableModel, OrderedModel):
    slug = models.SlugField(_("slug"), max_length=80, unique=True)

    title_es = models.CharField(_("título (ES)"), max_length=160)
    title_en = models.CharField(_("título (EN)"), max_length=160, blank=True)
    tagline_es = models.CharField(
        _("frase (ES)"),
        max_length=255,
        help_text=_("Una línea para la tarjeta."),
    )
    tagline_en = models.CharField(_("frase (EN)"), max_length=255, blank=True)
    summary_es = models.TextField(_("resumen (ES)"), help_text=_("Dos o tres frases."))
    summary_en = models.TextField(_("resumen (EN)"), blank=True)

    body_md_es = models.TextField(_("caso de estudio (ES)"), blank=True, help_text=_("Markdown."))
    body_md_en = models.TextField(_("caso de estudio (EN)"), blank=True)
    body_html_es = models.TextField(editable=False, blank=True)
    body_html_en = models.TextField(editable=False, blank=True)

    role_es = models.CharField(_("rol (ES)"), max_length=160, blank=True)
    role_en = models.CharField(_("rol (EN)"), max_length=160, blank=True)

    cover = models.ImageField(_("portada"), upload_to="projects/", blank=True)
    year = models.PositiveIntegerField(_("año"), db_index=True)
    featured = models.BooleanField(
        _("destacado"),
        default=False,
        help_text=_("Aparece en la página de inicio."),
    )

    repo_url = models.URLField(_("repositorio"), blank=True)
    live_url = models.URLField(_("sitio en vivo"), blank=True)
    store_url = models.URLField(_("tienda"), blank=True, help_text=_("Google Play, App Store…"))
    video_url = models.URLField(_("demostración en video"), blank=True)

    technologies = models.ManyToManyField(
        Technology,
        related_name="projects",
        verbose_name=_("tecnologías"),
        blank=True,
    )

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ("order", "-year")
        verbose_name = _("proyecto")
        verbose_name_plural = _("proyectos")
        indexes = [
            models.Index(fields=["status", "featured", "-year"], name="project_listing_idx"),
        ]

    def __str__(self) -> str:
        return self.title_es

    def save(self, *args, **kwargs) -> None:
        self.body_html_es = render_markdown(self.body_md_es)
        self.body_html_en = render_markdown(self.body_md_en)
        widen_update_fields(kwargs, {"body_html_es", "body_html_en"})
        super().save(*args, **kwargs)
        if self.is_published:
            schedule_site_rebuild(f"proyecto:{self.slug}")

    @property
    def links(self) -> dict[str, str]:
        """Enlaces no vacíos, listos para el frontend."""
        candidates = {
            "repo": self.repo_url,
            "live": self.live_url,
            "store": self.store_url,
            "video": self.video_url,
        }
        return {key: url for key, url in candidates.items() if url}


class ProjectImage(OrderedModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("proyecto"),
    )
    image = models.ImageField(_("imagen"), upload_to="projects/gallery/")
    caption_es = models.CharField(_("pie (ES)"), max_length=200, blank=True)
    caption_en = models.CharField(_("pie (EN)"), max_length=200, blank=True)

    class Meta(OrderedModel.Meta):
        verbose_name = _("imagen del proyecto")
        verbose_name_plural = _("galería")

    def __str__(self) -> str:
        return f"{self.project.slug} · {self.pk}"


class ProjectMetric(OrderedModel):
    """Dato duro del proyecto: «Publicada en Google Play», «3 formatos».

    Los números concretos convencen; los adjetivos, no.
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="metrics",
        verbose_name=_("proyecto"),
    )
    label_es = models.CharField(_("etiqueta (ES)"), max_length=80)
    label_en = models.CharField(_("etiqueta (EN)"), max_length=80, blank=True)
    value = models.CharField(_("valor"), max_length=60)

    class Meta(OrderedModel.Meta):
        verbose_name = _("métrica del proyecto")
        verbose_name_plural = _("métricas")

    def __str__(self) -> str:
        return f"{self.label_es}: {self.value}"
