from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from core.mixins import LanguageMixin
from core.throttling import SearchThrottle
from modules.blog.models import Category, Post, Tag
from modules.blog.serializers import (
    CategorySerializer,
    PostDetailSerializer,
    PostListSerializer,
    TagSerializer,
)


class CategoryListView(LanguageMixin, generics.ListAPIView):
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(posts__status="published").distinct().order_by("order")


class TagListView(LanguageMixin, generics.ListAPIView):
    serializer_class = TagSerializer
    pagination_class = None

    def get_queryset(self):
        return Tag.objects.filter(posts__status="published").distinct().order_by("name_es")


class PostListView(LanguageMixin, generics.ListAPIView):
    serializer_class = PostListSerializer

    def get_throttles(self):
        # La búsqueda hace LIKE sobre el cuerpo completo: más cara que un
        # listado y con su propio límite. Un listado normal no se penaliza.
        if self.request.query_params.get("q"):
            return [SearchThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        params = self.request.query_params
        queryset = Post.objects.live().with_related()

        if category := params.get("category"):
            queryset = queryset.filter(category__slug=category)
        if tag := params.get("tag"):
            queryset = queryset.filter(tags__slug=tag)
        if query := params.get("q"):
            queryset = queryset.search(query, self.get_language())

        return queryset.distinct()


class PostDetailView(LanguageMixin, generics.RetrieveAPIView):
    serializer_class = PostDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Post.objects.live().with_related()


@api_view(["POST"])
@throttle_classes([SearchThrottle])
def register_post_view(request, slug: str) -> Response:
    """Suma una lectura.

    Existe como endpoint aparte porque las páginas del blog son HTML estático:
    contar en el endpoint de detalle contaría las peticiones del build, no a
    los lectores. El frontend lo llama con `navigator.sendBeacon`, que no
    bloquea la navegación ni necesita framework alguno.
    """
    post = get_object_or_404(Post.objects.live(), slug=slug)
    post.register_view()
    return Response(status=status.HTTP_204_NO_CONTENT)
