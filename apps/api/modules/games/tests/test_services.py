"""Anti-trampa: es la lógica con más incentivo para ser atacada del sitio."""

import pytest

from core.exceptions import ServiceError
from modules.games import services
from modules.games.models import Game, GameKind, QuizOption, QuizQuestion

pytestmark = pytest.mark.django_db


@pytest.fixture
def snake():
    return Game.objects.create(
        slug="snake",
        kind=GameKind.ARCADE,
        name_es="Snake",
        description_es="x",
        max_plausible_score=5000,
        min_duration_ms=3000,
    )


@pytest.fixture
def quiz():
    game = Game.objects.create(
        slug="quiz",
        kind=GameKind.QUIZ,
        name_es="Quiz",
        description_es="x",
    )
    question = QuizQuestion.objects.create(game=game, text_es="¿Qué es WAL?", difficulty=2)
    QuizOption.objects.create(question=question, text_es="Correcta", is_correct=True)
    QuizOption.objects.create(question=question, text_es="Incorrecta", is_correct=False)
    return game


def _token(game):
    return services.start_session(game)["token"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # 18 caracteres tras limpiar, truncado al límite de 16.
        ("<script>alert(1)</script>", "scriptalert1scri"),
        ("pedro", "pedro"),
        ("  espacios   varios  ", "espacios varios"),
        ("", "anónimo"),
        ("!!!@@@###", "anónimo"),
        ("a" * 50, "a" * 16),
        ("Ñandú", "Ñandú"),
    ],
)
def test_nickname_sanitisation(raw, expected):
    assert services.sanitize_nickname(raw) == expected


def test_legit_score_is_accepted(snake):
    record, result = services.submit_score(
        game=snake,
        token=_token(snake),
        nickname="pedro",
        ip_hash="abc",
        score=420,
        duration_ms=60_000,
    )
    assert result.score == 420
    assert record.nickname == "pedro"


def test_token_cannot_be_replayed(snake):
    token = _token(snake)
    services.submit_score(
        game=snake, token=token, nickname="p", ip_hash="a", score=100, duration_ms=10_000
    )
    with pytest.raises(ServiceError) as exc:
        services.submit_score(
            game=snake, token=token, nickname="p", ip_hash="a", score=100, duration_ms=10_000
        )
    assert exc.value.detail.code == "invalid_session"


def test_implausible_score_is_rejected(snake):
    with pytest.raises(ServiceError) as exc:
        services.submit_score(
            game=snake,
            token=_token(snake),
            nickname="p",
            ip_hash="a",
            score=999_999,
            duration_ms=60_000,
        )
    assert exc.value.detail.code == "implausible_score"


def test_impossibly_fast_game_is_rejected(snake):
    with pytest.raises(ServiceError) as exc:
        services.submit_score(
            game=snake, token=_token(snake), nickname="p", ip_hash="a", score=100, duration_ms=10
        )
    assert exc.value.detail.code == "implausible_duration"


def test_token_issued_for_another_game_is_rejected(snake, quiz):
    with pytest.raises(ServiceError) as exc:
        services.submit_score(
            game=snake, token=_token(quiz), nickname="p", ip_hash="a", score=100, duration_ms=10_000
        )
    assert exc.value.detail.code == "token_mismatch"


def test_quiz_is_graded_on_the_server(quiz):
    question = quiz.questions.first()
    correct = question.options.get(is_correct=True)
    _record, result = services.submit_score(
        game=quiz,
        token=_token(quiz),
        nickname="p",
        ip_hash="a",
        answers=[{"question": question.pk, "option": correct.pk}],
    )
    assert result.score == 20  # dificultad 2 → 20 puntos
    assert result.correct_count == 1


def test_quiz_ignores_repeated_answers(quiz):
    """Enviar la misma pregunta diez veces no debe multiplicar la puntuación."""
    question = quiz.questions.first()
    correct = question.options.get(is_correct=True)
    _record, result = services.submit_score(
        game=quiz,
        token=_token(quiz),
        nickname="p",
        ip_hash="a",
        answers=[{"question": question.pk, "option": correct.pk}] * 10,
    )
    assert result.score == 20


def test_quiz_ignores_unknown_question_ids(quiz):
    _record, result = services.submit_score(
        game=quiz,
        token=_token(quiz),
        nickname="p",
        ip_hash="a",
        answers=[{"question": 999_999, "option": 999_999}],
    )
    assert result.score == 0


def test_client_supplied_score_is_ignored_in_quiz_mode(quiz):
    """La puntuación de un cuestionario SIEMPRE la calcula el servidor."""
    _record, result = services.submit_score(
        game=quiz,
        token=_token(quiz),
        nickname="p",
        ip_hash="a",
        score=99_999,
        answers=[],
    )
    assert result.score == 0
