"""Juegos interactivos y sus puntuaciones."""

from __future__ import annotations

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import OrderedModel, TimeStampedModel


class GameKind(models.TextChoices):
    """Cómo se puntúa el juego.

    QUIZ se corrige en el servidor a partir de las respuestas; ARCADE recibe
    una puntuación ya calculada por el cliente y solo puede validarse por
    plausibilidad. Son dos modelos de confianza distintos y el código tiene
    que distinguirlos explícitamente.
    """

    QUIZ = "quiz", _("Cuestionario (se corrige en el servidor)")
    ARCADE = "arcade", _("Arcade (puntuación enviada por el cliente)")


class Game(OrderedModel):
    slug = models.SlugField(_("slug"), max_length=40, unique=True)
    kind = models.CharField(
        _("tipo"),
        max_length=10,
        choices=GameKind.choices,
        default=GameKind.ARCADE,
    )
    name_es = models.CharField(_("nombre (ES)"), max_length=80)
    name_en = models.CharField(_("nombre (EN)"), max_length=80, blank=True)
    description_es = models.CharField(_("descripción (ES)"), max_length=255)
    description_en = models.CharField(_("descripción (EN)"), max_length=255, blank=True)
    icon = models.CharField(_("icono"), max_length=40, blank=True)
    cover = models.ImageField(
        _("portada"),
        upload_to="games/",
        blank=True,
        help_text=_("La que se ve en la tarjeta del listado de juegos."),
    )
    repo_url = models.URLField(
        _("repositorio"),
        blank=True,
        help_text=_(
            "Si el juego tiene su propio repositorio, se enlaza junto a la "
            "descripción. Vale para los que se desarrollaron aparte y luego "
            "se integraron aquí."
        ),
    )
    enabled = models.BooleanField(_("activo"), default=True, db_index=True)

    max_plausible_score = models.PositiveIntegerField(
        _("puntuación máxima creíble"),
        default=10_000,
        help_text=_("Cualquier envío por encima de este valor se rechaza."),
    )
    min_duration_ms = models.PositiveIntegerField(
        _("duración mínima (ms)"),
        default=3_000,
        help_text=_("Una partida más corta que esto no es humana."),
    )

    class Meta(OrderedModel.Meta):
        verbose_name = _("juego")
        verbose_name_plural = _("juegos")

    def __str__(self) -> str:
        return self.name_es


class QuizQuestion(OrderedModel):
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name=_("juego"),
    )
    text_es = models.TextField(_("pregunta (ES)"))
    text_en = models.TextField(_("pregunta (EN)"), blank=True)
    explanation_es = models.TextField(
        _("explicación (ES)"),
        blank=True,
        help_text=_("Se muestra después de responder. Es lo que convierte el juego en algo útil."),
    )
    explanation_en = models.TextField(_("explicación (EN)"), blank=True)
    difficulty = models.PositiveSmallIntegerField(
        _("dificultad"),
        default=1,
        choices=[(1, _("Fácil · 10 pts")), (2, _("Media · 20 pts")), (3, _("Difícil · 30 pts"))],
    )
    enabled = models.BooleanField(_("activa"), default=True)

    class Meta(OrderedModel.Meta):
        verbose_name = _("pregunta")
        verbose_name_plural = _("preguntas")

    def __str__(self) -> str:
        return self.text_es[:70]

    @property
    def points(self) -> int:
        return self.difficulty * 10


class QuizOption(OrderedModel):
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name=_("pregunta"),
    )
    text_es = models.CharField(_("opción (ES)"), max_length=255)
    text_en = models.CharField(_("opción (EN)"), max_length=255, blank=True)
    is_correct = models.BooleanField(_("es correcta"), default=False)

    class Meta(OrderedModel.Meta):
        verbose_name = _("opción")
        verbose_name_plural = _("opciones")

    def __str__(self) -> str:
        return self.text_es


class Score(TimeStampedModel):
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="scores",
        verbose_name=_("juego"),
    )
    nickname = models.CharField(_("apodo"), max_length=16)
    score = models.PositiveIntegerField(_("puntuación"), validators=[MinValueValidator(0)])
    duration_ms = models.PositiveIntegerField(_("duración (ms)"), default=0)
    meta = models.JSONField(_("detalle"), default=dict, blank=True)
    # Hash con sal, nunca la IP. Sirve igual para limitar abuso y deja de ser
    # un dato personal identificable.
    ip_hash = models.CharField(max_length=64, editable=False, db_index=True)

    class Meta:
        ordering = ("-score", "created_at")
        verbose_name = _("puntuación")
        verbose_name_plural = _("puntuaciones")
        indexes = [
            # Exactamente la consulta del ranking: filtrar por juego y ordenar
            # por puntuación descendente. Sin este índice, SQLite ordena la
            # tabla entera en cada petición.
            models.Index(fields=["game", "-score", "created_at"], name="score_ranking_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.nickname}: {self.score}"
