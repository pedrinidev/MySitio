"""El contrato de la API de juegos no puede filtrar las respuestas correctas."""

import pytest
from django.urls import reverse

from modules.games.models import Game, GameKind, QuizOption, QuizQuestion

pytestmark = pytest.mark.django_db


@pytest.fixture
def quiz():
    game = Game.objects.create(slug="quiz", kind=GameKind.QUIZ, name_es="Quiz", description_es="x")
    question = QuizQuestion.objects.create(game=game, text_es="Pregunta", difficulty=1)
    QuizOption.objects.create(question=question, text_es="Sí", is_correct=True)
    QuizOption.objects.create(question=question, text_es="No", is_correct=False)
    return game


def test_questions_never_expose_the_answer(api_client, quiz):
    """Si `is_correct` sale por la API, el juego entero deja de tener sentido."""
    response = api_client.get(reverse("v1:quiz-questions", args=["quiz"]))
    assert "is_correct" not in response.content.decode()


def test_disabled_game_is_not_listed(api_client, quiz):
    Game.objects.create(slug="oculto", name_es="Oculto", description_es="x", enabled=False)
    slugs = [g["slug"] for g in api_client.get(reverse("v1:game-list")).json()]
    assert slugs == ["quiz"]


def test_session_endpoint_returns_a_token(api_client, quiz):
    response = api_client.post(reverse("v1:game-session", args=["quiz"]))
    assert response.status_code == 201
    assert response.json()["token"]


def test_submitting_without_a_token_fails_validation(api_client, quiz):
    response = api_client.post(
        reverse("v1:score-submit", args=["quiz"]), {"nickname": "p"}, format="json"
    )
    assert response.status_code == 400
    assert "token" in response.json()["errors"]


def test_full_quiz_submission_through_the_api(api_client, quiz):
    """Recorre la ruta completa vista → servicio → respuesta.

    Existe porque las pruebas del servicio, al llamarlo directamente, no
    detectaron que la vista pasaba un argumento que la firma no aceptaba.
    Probar las capas por separado deja huecos justo en las costuras.
    """
    question = quiz.questions.first()
    correct = question.options.get(is_correct=True)

    token = api_client.post(reverse("v1:game-session", args=["quiz"])).json()["token"]

    response = api_client.post(
        reverse("v1:score-submit", args=["quiz"]) + "?lang=es",
        {
            "token": token,
            "nickname": "pedro",
            "answers": [{"question": question.pk, "option": correct.pk}],
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["score"] == 10  # dificultad 1 → 10 puntos
    assert body["correct"] == 1
    assert body["rank"] == 1
    # El repaso solo aparece DESPUÉS de corregir, nunca en /questions/.
    assert body["details"][0]["was_correct"] is True
    assert body["details"][0]["correct_option"] == correct.pk


def test_arcade_submission_through_the_api(api_client):
    """La misma costura, para el otro tipo de juego."""
    Game.objects.create(
        slug="snake",
        kind=GameKind.ARCADE,
        name_es="Snake",
        description_es="x",
        max_plausible_score=5000,
        min_duration_ms=3000,
    )
    token = api_client.post(reverse("v1:game-session", args=["snake"])).json()["token"]

    response = api_client.post(
        reverse("v1:score-submit", args=["snake"]),
        {"token": token, "nickname": "pedro", "score": 300, "duration_ms": 40_000},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["score"] == 300
