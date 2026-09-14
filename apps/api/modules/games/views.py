from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from core.i18n import normalize_language
from core.mixins import LanguageMixin
from core.security import request_ip_hash
from core.throttling import GameSessionThrottle, ScoreSubmitThrottle
from modules.games import services
from modules.games.models import Game, GameKind, QuizQuestion, Score
from modules.games.serializers import (
    GameSerializer,
    QuizQuestionSerializer,
    ScoreSerializer,
    ScoreSubmitSerializer,
)


def _get_enabled_game(slug: str) -> Game:
    return get_object_or_404(Game, slug=slug, enabled=True)


class GameListView(LanguageMixin, generics.ListAPIView):
    serializer_class = GameSerializer
    pagination_class = None
    queryset = Game.objects.filter(enabled=True).order_by("order")


class QuizQuestionListView(LanguageMixin, generics.ListAPIView):
    """Preguntas del cuestionario, sin las respuestas correctas."""

    serializer_class = QuizQuestionSerializer
    pagination_class = None

    def get_queryset(self):
        game = _get_enabled_game(self.kwargs["slug"])
        if game.kind != GameKind.QUIZ:
            return QuizQuestion.objects.none()
        return (
            QuizQuestion.objects.filter(game=game, enabled=True)
            .prefetch_related("options")
            .order_by("order")
        )


class LeaderboardView(LanguageMixin, generics.ListAPIView):
    serializer_class = ScoreSerializer
    pagination_class = None

    def get_queryset(self):
        game = _get_enabled_game(self.kwargs["slug"])
        try:
            limit = min(int(self.request.query_params.get("limit", 10)), 50)
        except ValueError:
            limit = 10
        return services.leaderboard(game, limit=limit)


@api_view(["POST"])
@throttle_classes([GameSessionThrottle])
def start_session(request, slug: str) -> Response:
    """Abre una partida y entrega el token necesario para enviar la puntuación."""
    game = _get_enabled_game(slug)
    return Response(services.start_session(game), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@throttle_classes([ScoreSubmitThrottle])
def submit_score(request, slug: str) -> Response:
    """Registra una puntuación validada.

    La vista hace tres cosas y ninguna más: valida la forma de la entrada,
    llama al servicio y serializa la salida. Toda decisión sobre si la
    puntuación es legítima está en services.py.
    """
    game = _get_enabled_game(slug)

    payload = ScoreSubmitSerializer(data=request.data)
    payload.is_valid(raise_exception=True)
    data = payload.validated_data

    record, result = services.submit_score(
        game=game,
        token=data["token"],
        nickname=data["nickname"],
        ip_hash=request_ip_hash(request),
        score=data["score"],
        duration_ms=data["duration_ms"],
        stats=data["stats"],
        answers=data["answers"],
        language=normalize_language(request.query_params.get("lang")),
    )

    rank = Score.objects.filter(game=game, score__gt=record.score).count() + 1

    return Response(
        {
            "score": result.score,
            "correct": result.correct_count,
            "total": result.total_questions,
            "nickname": record.nickname,
            "rank": rank,
            "details": result.details,
        },
        status=status.HTTP_201_CREATED,
    )
