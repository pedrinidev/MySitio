from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from core.admin import TimeStampedAdminMixin
from modules.blog.models import Category, Post, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name_es", "name_en", "slug", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name_es",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name_es", "name_en", "slug")
    search_fields = ("name_es", "name_en")
    prepopulated_fields = {"slug": ("name_es",)}


@admin.register(Post)
class PostAdmin(TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ("title_es", "category", "status", "published_at", "translation_state", "views")
    list_filter = ("status", "category", "tags", "published_at")
    search_fields = ("title_es", "title_en", "slug", "excerpt_es", "body_md_es")
    prepopulated_fields = {"slug": ("title_es",)}
    filter_horizontal = ("tags",)
    date_hierarchy = "published_at"
    save_on_top = True
    readonly_fields = (
        "created_at",
        "updated_at",
        "views",
        "reading_minutes_es",
        "reading_minutes_en",
    )

    fieldsets = (
        (
            "Publicación",
            {
                "fields": ("status", "published_at", "slug", "category", "tags"),
                "description": (
                    "Una fecha futura con estado «publicado» programa la " "salida del post."
                ),
            },
        ),
        ("Título y extracto", {"fields": (("title_es", "title_en"), ("excerpt_es", "excerpt_en"))}),
        (
            "Contenido",
            {
                "fields": (("body_md_es", "body_md_en"),),
                "description": "Markdown. Se convierte y sanea al guardar.",
            },
        ),
        ("Portada", {"fields": ("cover",)}),
        (
            "Métricas",
            {
                "fields": ("views", "reading_minutes_es", "reading_minutes_en"),
                "classes": ("collapse",),
            },
        ),
        ("Auditoría", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category")

    @admin.display(description="Traducción")
    def translation_state(self, obj: Post) -> str:
        if obj.title_en and obj.excerpt_en and obj.body_md_en:
            return format_html('<span style="color:#16a34a">✓ ES · EN</span>')
        return format_html('<span style="color:#ca8a04">solo ES</span>')
