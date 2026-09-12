"""Contrato público del módulo de proyectos."""

import pytest
from django.urls import reverse

from modules.projects.models import Project, Technology

pytestmark = pytest.mark.django_db


@pytest.fixture
def kotlin():
    return Technology.objects.create(name="Kotlin", slug="kotlin", category="mobile")


@pytest.fixture
def docker():
    return Technology.objects.create(name="Docker", slug="docker", category="devops")


@pytest.fixture
def published_project(kotlin):
    project = Project.objects.create(
        slug="mentepro",
        title_es="MentePro",
        title_en="MentePro",
        tagline_es="App Android",
        tagline_en="Android app",
        summary_es="Resumen",
        summary_en="Summary",
        year=2025,
        status="published",
        featured=True,
        store_url="https://play.google.com/store/apps/details?id=com.pedrini.mentepro",
    )
    project.technologies.add(kotlin)
    return project


def test_draft_projects_are_invisible(api_client, published_project):
    """Un borrador no puede filtrarse a la API pública bajo ninguna circunstancia."""
    Project.objects.create(
        slug="secreto",
        title_es="Secreto",
        tagline_es="x",
        summary_es="x",
        year=2026,
        status="draft",
    )
    response = api_client.get(reverse("v1:project-list"))
    slugs = [item["slug"] for item in response.json()["results"]]
    assert slugs == ["mentepro"]


def test_list_flattens_translations(api_client, published_project):
    response = api_client.get(reverse("v1:project-list"), {"lang": "en"})
    item = response.json()["results"][0]
    assert item["title"] == "MentePro"
    assert "title_es" not in item  # el sufijo de idioma nunca sale a la API


def test_empty_links_are_omitted(api_client, published_project):
    """Un enlace vacío no debe llegar al frontend como cadena vacía."""
    links = api_client.get(reverse("v1:project-list")).json()["results"][0]["links"]
    assert set(links) == {"store"}


def test_filter_by_technology(api_client, published_project, docker):
    other = Project.objects.create(
        slug="infra",
        title_es="Infra",
        tagline_es="x",
        summary_es="x",
        year=2026,
        status="published",
    )
    other.technologies.add(docker)

    response = api_client.get(reverse("v1:project-list"), {"tech": "docker"})
    assert [p["slug"] for p in response.json()["results"]] == ["infra"]


def test_filter_by_multiple_technologies_is_a_union(api_client, published_project, docker):
    """?tech=a,b devuelve los que usan CUALQUIERA, no los que usan ambas."""
    other = Project.objects.create(
        slug="infra",
        title_es="Infra",
        tagline_es="x",
        summary_es="x",
        year=2026,
        status="published",
    )
    other.technologies.add(docker)

    response = api_client.get(reverse("v1:project-list"), {"tech": "docker,kotlin"})
    assert response.json()["count"] == 2


def test_project_with_two_matching_technologies_is_not_duplicated(
    api_client, published_project, docker
):
    """El JOIN del filtro duplicaría filas sin el distinct()."""
    published_project.technologies.add(docker)
    response = api_client.get(reverse("v1:project-list"), {"tech": "docker,kotlin"})
    assert response.json()["count"] == 1


def test_detail_includes_body_but_list_does_not(api_client, published_project):
    """El listado no debe arrastrar el caso de estudio completo por tarjeta."""
    published_project.body_md_es = "## Caso\n\nTexto largo."
    published_project.save()

    listed = api_client.get(reverse("v1:project-list")).json()["results"][0]
    assert "body_html" not in listed

    detail = api_client.get(reverse("v1:project-detail", args=[published_project.slug])).json()
    assert "<h2" in detail["body_html"]


def test_technology_list_only_shows_used_technologies(api_client, published_project, docker):
    """Ofrecer un filtro que devuelve cero resultados es una mala experiencia."""
    response = api_client.get(reverse("v1:technology-list"))
    assert [t["slug"] for t in response.json()] == ["kotlin"]
