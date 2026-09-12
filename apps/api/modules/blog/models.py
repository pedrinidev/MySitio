"""Blog bilingüe en Markdown, gestionado desde el admin."""

from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.markdown import estimate_reading_minutes, render_markdown
from core.models import (
    OrderedModel,
    PublishableModel,
    PublishableQuerySet,
    TimeStampedModel,
    widen_update_fields,
)
from core.webhooks import schedule_site_rebuild


class Category(OrderedModel):
    slug = models.SlugField(_("slug"), max_length=60, unique=True)
    name_es = models.CharField(_("nombre (ES)"), max_length=80)
    name_en = models.CharField(_("nombre (EN)"), max_length=80, blank=True)
    description_es = models.CharField(_("descripción (ES)"), max_length=200, blank=True)
    description_en = models.CharField(_("descripción (EN)"), max_length=200, blank=True)

    class Meta(OrderedModel.Meta):
        verbose_name = _("categoría")
        verbose_name_plural = _("categorías")

    def __str__(self) -> str:
        return self.name_es


class Tag(models.Model):
    slug = models.SlugField(_("slug"), max_length=60, unique=True)
    name_es = models.CharField(_("nombre (ES)"), max_length=60)
    name_en = models.CharField(_("nombre (EN)"), max_length=60, blank=True)

    class Meta:
        ordering = ("name_es",)
        verbose_name = _("etiqueta")
        verbose_name_plural = _("etiquetas")

    def __str__(self) -> str:
        return self.name_es


class PostQuerySet(PublishableQuerySet):
    def live(self) -> PostQuerySet:
        """Publicados Y con fecha ya alcanzada.

        Separar `status` de `published_at` permite programar una publicación:
        se deja en «publicado» con fecha futura y aparece sola. Filtrar solo
        por estado haría visible el post de inmediato.
        """
        return self.published().filter(published_at__lte=timezone.now())

    def with_related(self) -> PostQuerySet:
        return self.select_related("category").prefetch_related("tags")

    def search(self, query: str, language: str = "es") -> PostQuerySet:
        """Búsqueda por subcadena en el idioma indicado.

        `icontains` es suficiente mientras haya decenas de posts: SQLite
        resuelve un LIKE sobre esa escala en milisegundos. La migración a FTS5
        está planificada (ver docs/decisions.md, ADR-006) para cuando el
        volumen la justifique — no antes.
        """
        if not query or not query.strip():
            return self
        term = query.strip()
        lookup = models.Q(**{f"title_{language}__icontains": term})
        lookup |= models.Q(**{f"excerpt_{language}__icontains": term})
        lookup |= models.Q(**{f"body_md_{language}__icontains": term})
        return self.filter(lookup)


class Post(TimeStampedModel, PublishableModel):
    slug = models.SlugField(_("slug"), max_length=100, unique=True)

    title_es = models.CharField(_("título (ES)"), max_length=200)
    title_en = models.CharField(_("título (EN)"), max_length=200, blank=True)
    excerpt_es = models.TextField(
        _("extracto (ES)"),
        max_length=500,
        help_text=_("También se usa como meta description. Máximo 500 caracteres."),
    )
    excerpt_en = models.TextField(_("extracto (EN)"), max_length=500, blank=True)

    body_md_es = models.TextField(_("contenido (ES)"), help_text=_("Markdown."))
    body_md_en = models.TextField(_("contenido (EN)"), blank=True)
    body_html_es = models.TextField(editable=False, blank=True)
    body_html_en = models.TextField(editable=False, blank=True)

    cover = models.ImageField(_("portada"), upload_to="blog/", blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="posts",
        verbose_name=_("categoría"),
    )
    tags = models.ManyToManyField(
        Tag, related_name="posts", blank=True, verbose_name=_("etiquetas")
    )

    published_at = models.DateTimeField(
        _("fecha de publicación"),
        default=timezone.now,
        db_index=True,
        help_text=_("Una fecha futura programa la publicación."),
    )
    reading_minutes_es = models.PositiveSmallIntegerField(default=1, editable=False)
    reading_minutes_en = models.PositiveSmallIntegerField(default=1, editable=False)
    views = models.PositiveIntegerField(_("lecturas"), default=0, editable=False)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ("-published_at",)
        verbose_name = _("publicación")
        verbose_name_plural = _("publicaciones")
        indexes = [
            models.Index(fields=["status", "-published_at"], name="post_listing_idx"),
        ]

    def __str__(self) -> str:
        return self.title_es

    def save(self, *args, **kwargs) -> None:
        # El HTML y el tiempo de lectura se derivan del Markdown: se calculan
        # una vez aquí, no en cada petición.
        self.body_html_es = render_markdown(self.body_md_es)
        self.body_html_en = render_markdown(self.body_md_en)
        self.reading_minutes_es = estimate_reading_minutes(self.body_md_es)
        self.reading_minutes_en = estimate_reading_minutes(self.body_md_en or self.body_md_es)
        widen_update_fields(
            kwargs,
            {"body_html_es", "body_html_en", "reading_minutes_es", "reading_minutes_en"},
        )
        super().save(*args, **kwargs)
        if self.is_published:
            schedule_site_rebuild(f"post:{self.slug}")

    @property
    def is_live(self) -> bool:
        return self.is_published and self.published_at <= timezone.now()

    def register_view(self) -> None:
        """Suma una lectura sin condición de carrera.

        `F()` delega la suma a SQLite (`views = views + 1`). Leer el valor en
        Python, sumarle uno y guardarlo perdería lecturas simultáneas.
        `update()` además evita disparar `save()` y, con él, una
        reconstrucción del sitio por cada visita.
        """
        Post.objects.filter(pk=self.pk).update(views=models.F("views") + 1)
