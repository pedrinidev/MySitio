from __future__ import annotations

from rest_framework import serializers

from core.serializers import AbsoluteImageField, TranslatedField
from modules.projects.models import Project, ProjectImage, ProjectMetric, Technology


class TechnologySerializer(serializers.ModelSerializer):
    class Meta:
        model = Technology
        fields = ("slug", "name", "category", "color", "icon")


class ProjectImageSerializer(serializers.ModelSerializer):
    caption = TranslatedField()
    url = AbsoluteImageField("image")

    class Meta:
        model = ProjectImage
        fields = ("url", "caption")


class ProjectMetricSerializer(serializers.ModelSerializer):
    label = TranslatedField()

    class Meta:
        model = ProjectMetric
        fields = ("label", "value")


class ProjectListSerializer(serializers.ModelSerializer):
    """Versión ligera para el grid.

    Deliberadamente NO incluye `body_html`: un caso de estudio son varios KB y
    multiplicarlos por doce tarjetas convierte un listado en una descarga.
    """

    title = TranslatedField()
    tagline = TranslatedField()
    summary = TranslatedField()
    cover_url = AbsoluteImageField("cover")
    technologies = TechnologySerializer(many=True, read_only=True)
    links = serializers.DictField(read_only=True)

    class Meta:
        model = Project
        fields = (
            "slug",
            "title",
            "tagline",
            "summary",
            "cover_url",
            "year",
            "featured",
            "technologies",
            "links",
        )


class ProjectDetailSerializer(ProjectListSerializer):
    body_html = TranslatedField()
    role = TranslatedField()
    images = ProjectImageSerializer(many=True, read_only=True)
    metrics = ProjectMetricSerializer(many=True, read_only=True)

    class Meta(ProjectListSerializer.Meta):
        fields = (*ProjectListSerializer.Meta.fields, "body_html", "role", "images", "metrics")
