"""Contrato público del blog, incluida la publicación programada."""

import pytest
from django.urls import reverse
from django.utils import timezone

from modules.blog.models import Category, Post

pytestmark = pytest.mark.django_db


@pytest.fixture
def category():
    return Category.objects.create(slug="infra", name_es="Infraestructura", name_en="Infra")


def _make_post(category, **overrides):
    defaults = {
        "slug": "post-uno",
        "title_es": "Docker en un droplet pequeño",
        "title_en": "Docker on a small droplet",
        "excerpt_es": "Resumen",
        "excerpt_en": "Summary",
        "body_md_es": "Contenido sobre contenedores y swap.",
        "body_md_en": "Content about containers and swap.",
        "category": category,
        "status": "published",
    }
    return Post.objects.create(**{**defaults, **overrides})


def test_draft_is_hidden(api_client, category):
    _make_post(category, slug="borrador", status="draft")
    assert api_client.get(reverse("v1:post-list")).json()["count"] == 0


def test_future_post_is_hidden(api_client, category):
    """Estado «publicado» con fecha futura significa programado, no visible."""
    _make_post(
        category,
        slug="programado",
        published_at=timezone.now() + timezone.timedelta(days=3),
    )
    assert api_client.get(reverse("v1:post-list")).json()["count"] == 0


def test_search_matches_body(api_client, category):
    _make_post(category)
    response = api_client.get(reverse("v1:post-list"), {"q": "swap"})
    assert response.json()["count"] == 1


def test_search_respects_language(api_client, category):
    """Buscar en inglés no debe encontrar coincidencias solo presentes en español."""
    _make_post(category, body_md_es="palabra exclusiva del español", body_md_en="only english")
    assert (
        api_client.get(reverse("v1:post-list"), {"q": "exclusiva", "lang": "en"}).json()["count"]
        == 0
    )
    assert (
        api_client.get(reverse("v1:post-list"), {"q": "exclusiva", "lang": "es"}).json()["count"]
        == 1
    )


def test_markdown_is_rendered_on_save(api_client, category):
    post = _make_post(category, body_md_es="## Título\n\nTexto.")
    assert "<h2" in post.body_html_es


def test_reading_time_is_computed(api_client, category):
    post = _make_post(category, body_md_es=" ".join(["palabra"] * 400))
    assert post.reading_minutes_es == 2


def test_view_counter_increments_without_touching_save(api_client, category):
    """register_view usa update(): no debe disparar el render ni el webhook."""
    post = _make_post(category)
    api_client.post(reverse("v1:post-view", args=[post.slug]))
    post.refresh_from_db()
    assert post.views == 1


def test_view_counter_rejects_unknown_slug(api_client, category):
    assert api_client.post(reverse("v1:post-view", args=["no-existe"])).status_code == 404
