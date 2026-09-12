from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from modules.games.models import Game, QuizOption, QuizQuestion, Score


class QuizOptionInline(admin.TabularInline):
    model = QuizOption
    extra = 4
    fields = ("text_es", "text_en", "is_correct", "order")


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "game", "difficulty", "enabled", "answer_check", "order")
    list_filter = ("game", "difficulty", "enabled")
    list_editable = ("enabled", "order")
    search_fields = ("text_es", "text_en")
    inlines = (QuizOptionInline,)

    def get_queryset(self, request):
        from django.db.models import Count, Q

        return (
            super()
            .get_queryset(request)
            .select_related("game")
            .annotate(_correct=Count("options", filter=Q(options__is_correct=True)))
        )

    @admin.display(description="Respuesta")
    def answer_check(self, obj) -> str:
        """Avisa de preguntas mal cargadas.

        Una pregunta sin opción correcta, o con dos, es un fallo silencioso:
        el juego funciona pero puntúa mal. Mejor verlo en el listado que
        descubrirlo por un correo de alguien que jugó.
        """
        count = obj._correct
        if count == 1:
            return format_html('<span style="color:#16a34a">✓</span>')
        if count == 0:
            return format_html('<span style="color:#dc2626">sin respuesta correcta</span>')
        return format_html('<span style="color:#dc2626">{} correctas</span>', count)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("name_es", "slug", "kind", "enabled", "score_count", "order")
    list_editable = ("enabled", "order")
    list_filter = ("kind", "enabled")
    prepopulated_fields = {"slug": ("name_es",)}
    fieldsets = (
        (
            "Identidad",
            {
                "fields": (
                    "slug",
                    "kind",
                    ("name_es", "name_en"),
                    ("description_es", "description_en"),
                    "icon",
                )
            },
        ),
        ("Publicación", {"fields": ("enabled", "order")}),
        (
            "Anti-trampa",
            {
                "fields": ("max_plausible_score", "min_duration_ms"),
                "description": "Límites por encima/debajo de los cuales un envío se rechaza. "
                "Solo aplican a los juegos de tipo arcade.",
            },
        ),
    )

    def get_queryset(self, request):
        from django.db.models import Count

        return super().get_queryset(request).annotate(_scores=Count("scores"))

    @admin.display(description="Partidas", ordering="_scores")
    def score_count(self, obj) -> int:
        return obj._scores


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("nickname", "game", "score", "duration_ms", "created_at")
    list_filter = ("game", "created_at")
    search_fields = ("nickname",)
    readonly_fields = (
        "game",
        "nickname",
        "score",
        "duration_ms",
        "meta",
        "ip_hash",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request) -> bool:
        # Las puntuaciones solo entran por la API validada. Crearlas a mano
        # desde el admin saltaría el token y la comprobación de plausibilidad.
        return False
