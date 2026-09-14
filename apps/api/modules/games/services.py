"""Lógica de negocio de los juegos.

Aquí vive todo lo que decide si una puntuación es legítima. Las vistas solo
validan la forma de la petición y delegan: si esta lógica estuviera en la
vista, sería imposible probarla sin montar una petición HTTP completa.

Sobre el anti-trampa: **no es infalible y no pretende serlo.** Todo lo que
corre en el navegador es manipulable. El objetivo es que hacer trampa cueste
trabajo deliberado en vez de abrir el inspector y editar un número.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from django.conf import settings
from django.db.models import QuerySet

from core.exceptions import ServiceError
from core.i18n import translate
from core.security import consume_signed_token, issue_signed_token
from modules.games.models import Game, GameKind, QuizOption, QuizQuestion, Score

logger = logging.getLogger("mysite.games")

# Espacio de nombres de la firma, no un secreto: la clave real es
# GAME_TOKEN_SECRET. El salt solo impide que un token válido en un
# contexto sirva en otro.
TOKEN_SALT = "games.session"  # noqa: S105

# Letras (con acentos), dígitos, espacio, guion y guion bajo. Nada más:
# el apodo se pinta en el ranking y todo lo demás es superficie de XSS.
_NICKNAME_ALLOWED = re.compile(r"[^\w\s\-áéíóúüñÁÉÍÓÚÜÑ]", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")
_DEFAULT_NICKNAME = "anónimo"


@dataclass(frozen=True)
class ScoreResult:
    """Resultado de una partida ya validada."""

    score: int
    correct_count: int = 0
    total_questions: int = 0
    # Repaso pregunta a pregunta, solo para cuestionarios. Se devuelve DESPUÉS
    # de corregir: es lo que convierte el juego en algo de lo que se aprende,
    # sin haber filtrado las respuestas antes de jugar.
    details: tuple[dict, ...] = ()


def sanitize_nickname(raw: str) -> str:
    """Normaliza un apodo hasta dejarlo seguro para mostrar.

    Se sanea en la entrada además de escapar en la salida. Redundante a
    propósito: la defensa que sobrevive es la que no depende de que la otra
    capa esté bien puesta.
    """
    cleaned = _NICKNAME_ALLOWED.sub("", raw or "")
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()[:16]
    return cleaned or _DEFAULT_NICKNAME


def start_session(game: Game) -> dict[str, object]:
    """Abre una partida y devuelve el token que habrá que presentar al enviar.

    El token lleva firma y marca de tiempo. Sin él, cualquiera puede publicar
    puntuaciones con un solo `curl`.
    """
    token = issue_signed_token({"game": game.slug}, salt=TOKEN_SALT)
    return {"token": token, "expires_in": settings.GAME_TOKEN_TTL_SECONDS}


def _validate_token(game: Game, token: str) -> None:
    payload = consume_signed_token(token, salt=TOKEN_SALT, max_age=settings.GAME_TOKEN_TTL_SECONDS)
    if payload is None:
        raise ServiceError(
            "La partida caducó o el token ya se usó. Volvé a empezar.",
            code="invalid_session",
        )
    if payload.get("game") != game.slug:
        # Token válido pero emitido para otro juego: intento de reutilización.
        logger.warning("Token de %s presentado en %s", payload.get("game"), game.slug)
        raise ServiceError("El token no corresponde a este juego.", code="token_mismatch")


def _assert_plausible(game: Game, score: int, duration_ms: int) -> None:
    """Rechaza lo que ningún humano podría haber conseguido."""
    if score > game.max_plausible_score:
        raise ServiceError(
            f"Puntuación fuera de rango (máximo {game.max_plausible_score}).",
            code="implausible_score",
        )
    if duration_ms < game.min_duration_ms:
        raise ServiceError(
            "La partida duró menos de lo humanamente posible.",
            code="implausible_duration",
        )


def grade_quiz(game: Game, answers: list[dict], language: str = "es") -> ScoreResult:
    """Corrige el cuestionario **en el servidor**.

    El cliente envía qué opción eligió, nunca si acertó. Enviar `is_correct`
    al navegador equivaldría a publicar las respuestas junto a las preguntas.

    Devuelve además el repaso: qué opción era la correcta y por qué. Esa
    información solo sale de aquí, una vez que la partida ya está cerrada.
    """
    questions: QuerySet[QuizQuestion] = QuizQuestion.objects.filter(
        game=game, enabled=True
    ).prefetch_related("options")
    questions_by_id = {question.pk: question for question in questions}

    correct_option_ids = set(
        QuizOption.objects.filter(
            question__game=game, question__enabled=True, is_correct=True
        ).values_list("pk", flat=True)
    )

    # Mapa pregunta → opción correcta, para poder devolver el repaso.
    correct_by_question = {
        option.question_id: option.pk
        for option in QuizOption.objects.filter(
            question__game=game, question__enabled=True, is_correct=True
        )
    }

    score = 0
    correct_count = 0
    seen: set[int] = set()
    details: list[dict] = []

    for answer in answers:
        question_id = answer.get("question")
        option_id = answer.get("option")

        question = questions_by_id.get(question_id)
        if question is None or question_id in seen:
            # Pregunta inexistente o repetida: se ignora en silencio en vez de
            # devolver un error. No hay que darle al que prueba un mapa de qué
            # identificadores existen.
            continue
        seen.add(question_id)

        was_correct = option_id in correct_option_ids
        if was_correct:
            score += question.points
            correct_count += 1

        details.append(
            {
                "question": question_id,
                "chosen_option": option_id,
                "correct_option": correct_by_question.get(question_id),
                "was_correct": was_correct,
                "explanation": translate(question, "explanation", language),
            }
        )

    return ScoreResult(
        score=score,
        correct_count=correct_count,
        total_questions=len(questions_by_id),
        details=tuple(details),
    )


def submit_score(
    *,
    game: Game,
    token: str,
    nickname: str,
    ip_hash: str,
    score: int = 0,
    duration_ms: int = 0,
    answers: list[dict] | None = None,
    stats: dict | None = None,
    language: str = "es",
) -> tuple[Score, ScoreResult]:
    """Valida y registra una puntuación. Único camino de escritura del módulo."""
    _validate_token(game, token)

    if game.kind == GameKind.QUIZ:
        result = grade_quiz(game, answers or [], language)
    else:
        _assert_plausible(game, score, duration_ms)
        result = ScoreResult(score=score)

    record = Score.objects.create(
        game=game,
        nickname=sanitize_nickname(nickname),
        score=result.score,
        duration_ms=duration_ms,
        ip_hash=ip_hash,
        meta=(
            {"correct": result.correct_count, "total": result.total_questions}
            if game.kind == GameKind.QUIZ
            # En los arcade, lo que mande el juego ya filtrado por el
            # serializador: mejor racha, rondas superadas, aciertos.
            else dict(stats or {})
        ),
    )
    logger.info("Puntuación registrada: %s en %s = %s", record.nickname, game.slug, result.score)
    return record, result


def leaderboard(game: Game, limit: int = 10) -> QuerySet[Score]:
    """Mejores puntuaciones. El índice score_ranking_idx cubre esta consulta."""
    return Score.objects.filter(game=game).order_by("-score", "created_at")[:limit]
