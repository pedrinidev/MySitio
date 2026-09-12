from __future__ import annotations

from django.db.models import Prefetch
from rest_framework import generics
from rest_framework.exceptions import NotFound

from core.mixins import LanguageMixin
from modules.site.models import ExperienceItem, Profile, Skill, SkillGroup
from modules.site.serializers import ProfileSerializer


class ProfileView(LanguageMixin, generics.RetrieveAPIView):
    """Perfil completo en una sola respuesta.

    El frontend lo consume una vez por build (es contenido estático), así que
    fragmentarlo en cuatro endpoints solo añadiría latencia al pipeline.
    """

    serializer_class = ProfileSerializer

    def get_object(self) -> Profile:
        # Prefetch explícito: sin esto, serializar grupos y habilidades genera
        # una consulta por grupo. Con 5 grupos son 6 consultas donde debería
        # haber 2.
        profile = Profile.objects.prefetch_related(
            "socials",
            Prefetch(
                "skill_groups",
                queryset=SkillGroup.objects.prefetch_related(
                    Prefetch("skills", queryset=Skill.objects.order_by("order"))
                ),
            ),
            Prefetch("experience", queryset=ExperienceItem.objects.order_by("-start_date")),
        ).first()
        if profile is None:
            raise NotFound(
                "Todavía no se cargó el perfil. Creálo desde el panel de administración."
            )
        return profile
