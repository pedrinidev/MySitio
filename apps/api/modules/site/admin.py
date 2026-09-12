from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from core.admin import SingletonAdminMixin, TimeStampedAdminMixin
from modules.site.models import ExperienceItem, Profile, Skill, SkillGroup, SocialLink


class SocialLinkInline(admin.TabularInline):
    model = SocialLink
    extra = 1


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 3


class ExperienceInline(admin.StackedInline):
    model = ExperienceItem
    extra = 0
    fields = (
        ("role_es", "role_en"),
        "organization",
        ("start_date", "end_date"),
        ("description_es", "description_en"),
        ("highlights_es", "highlights_en"),
        "order",
    )


@admin.register(Profile)
class ProfileAdmin(SingletonAdminMixin, TimeStampedAdminMixin, admin.ModelAdmin):
    inlines = (SocialLinkInline, ExperienceInline)
    fieldsets = (
        ("Identidad", {"fields": ("full_name", "avatar", ("role_es", "role_en"))}),
        ("Hero", {"fields": (("headline_es", "headline_en"),)}),
        (
            "Biografía",
            {
                "fields": (("bio_es", "bio_en"),),
                "description": "Se escribe en Markdown y se convierte a HTML al guardar.",
            },
        ),
        (
            "Contacto",
            {
                "fields": (
                    "email",
                    "phone",
                    ("location_es", "location_en"),
                    ("availability_es", "availability_en"),
                )
            },
        ),
        ("Curriculum", {"fields": (("cv_es", "cv_en"),)}),
        ("Auditoría", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(SkillGroup)
class SkillGroupAdmin(admin.ModelAdmin):
    list_display = ("name_es", "name_en", "skill_count", "order")
    list_editable = ("order",)
    inlines = (SkillInline,)

    def get_queryset(self, request):
        # annotate en vez de contar por fila: una consulta en lugar de N.
        from django.db.models import Count

        return super().get_queryset(request).annotate(_skill_count=Count("skills"))

    @admin.display(description="Habilidades", ordering="_skill_count")
    def skill_count(self, obj) -> str:
        return format_html("<b>{}</b>", obj._skill_count)
