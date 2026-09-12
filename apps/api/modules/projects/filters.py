from __future__ import annotations

import django_filters as filters

from modules.projects.models import Project


class ProjectFilter(filters.FilterSet):
    """Filtros del listado de proyectos.

    `tech` acepta varios slugs separados por coma (`?tech=kotlin,docker`) con
    semántica O: «proyectos que usen alguna de estas». Es lo que espera quien
    usa un filtro de facetas — la semántica Y devolvería casi siempre vacío.
    """

    tech = filters.CharFilter(method="filter_by_technologies")
    featured = filters.BooleanFilter(field_name="featured")
    year = filters.NumberFilter(field_name="year")

    class Meta:
        model = Project
        fields = ("tech", "featured", "year")

    def filter_by_technologies(self, queryset, name: str, value: str):
        slugs = [slug.strip() for slug in value.split(",") if slug.strip()]
        return queryset.by_technologies(slugs)
