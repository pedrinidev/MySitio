from __future__ import annotations

from rest_framework import generics

from core.mixins import LanguageMixin
from modules.projects.filters import ProjectFilter
from modules.projects.models import Project, Technology
from modules.projects.serializers import (
    ProjectDetailSerializer,
    ProjectListSerializer,
    TechnologySerializer,
)


class TechnologyListView(LanguageMixin, generics.ListAPIView):
    """Catálogo de tecnologías, para poblar el filtro del frontend."""

    serializer_class = TechnologySerializer
    pagination_class = None  # son ~20 registros: paginar sería un estorbo

    def get_queryset(self):
        # Solo las que tienen al menos un proyecto publicado: ofrecer un filtro
        # que devuelve cero resultados es una mala experiencia de uso.
        return (
            Technology.objects.filter(projects__status="published")
            .distinct()
            .order_by("order", "name")
        )


class ProjectListView(LanguageMixin, generics.ListAPIView):
    serializer_class = ProjectListSerializer
    filterset_class = ProjectFilter

    def get_queryset(self):
        return Project.objects.published().with_related()


class ProjectDetailView(LanguageMixin, generics.RetrieveAPIView):
    serializer_class = ProjectDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Project.objects.published().with_related().prefetch_related("images", "metrics")
