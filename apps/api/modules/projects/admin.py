from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from core.admin import TimeStampedAdminMixin
from modules.projects.models import Project, ProjectImage, ProjectMetric, Technology


@admin.register(Technology)
class TechnologyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "category", "swatch", "order")
    list_editable = ("order",)
    list_filter = ("category",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Color")
    def swatch(self, obj: Technology) -> str:
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;'
            'border-radius:4px;background:{};border:1px solid #0002"></span> {}',
            obj.color,
            obj.color,
        )


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1
    fields = ("image", "caption_es", "caption_en", "order")


class ProjectMetricInline(admin.TabularInline):
    model = ProjectMetric
    extra = 1
    fields = ("label_es", "label_en", "value", "order")


@admin.register(Project)
class ProjectAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ("title_es", "year", "status", "featured", "translation_state", "order")
    list_editable = ("status", "featured", "order")
    list_filter = ("status", "featured", "year", "technologies")
    search_fields = ("title_es", "title_en", "slug", "summary_es")
    prepopulated_fields = {"slug": ("title_es",)}
    filter_horizontal = ("technologies",)
    inlines = (ProjectMetricInline, ProjectImageInline)
    save_on_top = True

    fieldsets = (
        ("Publicación", {"fields": (("status", "featured", "order"), "slug", "year")}),
        (
            "Título y resumen",
            {
                "fields": (
                    ("title_es", "title_en"),
                    ("tagline_es", "tagline_en"),
                    ("summary_es", "summary_en"),
                )
            },
        ),
        (
            "Caso de estudio",
            {
                "fields": (("body_md_es", "body_md_en"), ("role_es", "role_en")),
                "description": "Markdown. Se convierte y sanea al guardar.",
            },
        ),
        (
            "Medios y enlaces",
            {"fields": ("cover", "repo_url", "live_url", "store_url", "video_url")},
        ),
        ("Tecnologías", {"fields": ("technologies",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("technologies")

    @admin.display(description="Traducción")
    def translation_state(self, obj: Project) -> str:
        missing = [
            label
            for label, value in (
                ("título", obj.title_en),
                ("frase", obj.tagline_en),
                ("resumen", obj.summary_en),
                ("caso", obj.body_md_en),
            )
            if not value
        ]
        if not missing:
            return format_html('<span style="color:#16a34a">✓ ES · EN</span>')
        return format_html('<span style="color:#ca8a04">falta EN: {}</span>', ", ".join(missing))
