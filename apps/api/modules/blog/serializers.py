from __future__ import annotations

from rest_framework import serializers

from core.serializers import AbsoluteImageField, TranslatedField
from modules.blog.models import Category, Post, Tag


class CategorySerializer(serializers.ModelSerializer):
    name = TranslatedField()
    description = TranslatedField()

    class Meta:
        model = Category
        fields = ("slug", "name", "description")


class TagSerializer(serializers.ModelSerializer):
    name = TranslatedField()

    class Meta:
        model = Tag
        fields = ("slug", "name")


class PostListSerializer(serializers.ModelSerializer):
    title = TranslatedField()
    excerpt = TranslatedField()
    cover_url = AbsoluteImageField("cover")
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    reading_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "slug",
            "title",
            "excerpt",
            "cover_url",
            "category",
            "tags",
            "published_at",
            "reading_minutes",
        )

    def get_reading_minutes(self, obj: Post) -> int:
        language = self.context.get("lang", "es")
        return getattr(obj, f"reading_minutes_{language}", obj.reading_minutes_es)


class PostDetailSerializer(PostListSerializer):
    body_html = TranslatedField()

    class Meta(PostListSerializer.Meta):
        fields = (*PostListSerializer.Meta.fields, "body_html", "views")
