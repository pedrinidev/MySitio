from __future__ import annotations

from rest_framework import serializers

from core.serializers import AbsoluteImageField, TranslatedField
from modules.site.models import ExperienceItem, Profile, Skill, SkillGroup, SocialLink


class SocialLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = ("name", "url", "icon")


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ("name", "level", "is_primary")


class SkillGroupSerializer(serializers.ModelSerializer):
    name = TranslatedField()
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = SkillGroup
        fields = ("name", "skills")


class ExperienceItemSerializer(serializers.ModelSerializer):
    role = TranslatedField()
    description = TranslatedField()
    highlights = serializers.SerializerMethodField()

    class Meta:
        model = ExperienceItem
        fields = (
            "role",
            "organization",
            "start_date",
            "end_date",
            "is_current",
            "description",
            "highlights",
        )

    def get_highlights(self, obj: ExperienceItem) -> list[str]:
        """Convierte el textarea (un aporte por línea) en una lista.

        Se hace aquí y no en el modelo porque es una preocupación de formato de
        salida: la base guarda el texto tal como lo escribió el autor.
        """
        language = self.context.get("lang", "es")
        raw = getattr(obj, f"highlights_{language}", "") or obj.highlights_es
        return [line.strip() for line in raw.splitlines() if line.strip()]


class ProfileSerializer(serializers.ModelSerializer):
    role = TranslatedField()
    headline = TranslatedField()
    bio_html = TranslatedField()
    location = TranslatedField()
    availability = TranslatedField()
    avatar_url = AbsoluteImageField("avatar")
    cv_url = serializers.SerializerMethodField()
    socials = SocialLinkSerializer(many=True, read_only=True)
    skill_groups = SkillGroupSerializer(many=True, read_only=True)
    experience = ExperienceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = (
            "full_name",
            "role",
            "headline",
            "bio_html",
            "email",
            "phone",
            "location",
            "availability",
            "avatar_url",
            "cv_url",
            "socials",
            "skill_groups",
            "experience",
        )

    def get_cv_url(self, obj: Profile) -> str | None:
        """CV en el idioma pedido, con caída al español si no hay versión."""
        language = self.context.get("lang", "es")
        cv = getattr(obj, f"cv_{language}", None) or obj.cv_es
        if not cv:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(cv.url) if request else cv.url
