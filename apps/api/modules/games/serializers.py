from __future__ import annotations

from rest_framework import serializers

from core.serializers import TranslatedField
from modules.games.models import Game, QuizOption, QuizQuestion, Score


class GameSerializer(serializers.ModelSerializer):
    name = TranslatedField()
    description = TranslatedField()

    class Meta:
        model = Game
        fields = ("slug", "kind", "name", "description", "icon")


class QuizOptionSerializer(serializers.ModelSerializer):
    text = TranslatedField()

    class Meta:
        model = QuizOption
        # `is_correct` NO se expone jamás. Es la razón entera por la que la
        # corrección vive en el servidor: mandarlo aquí regalaría el juego.
        fields = ("id", "text")


class QuizQuestionSerializer(serializers.ModelSerializer):
    text = TranslatedField()
    options = QuizOptionSerializer(many=True, read_only=True)

    class Meta:
        model = QuizQuestion
        fields = ("id", "text", "difficulty", "points", "options")


class ScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Score
        fields = ("nickname", "score", "duration_ms", "meta", "created_at")


class ScoreSubmitSerializer(serializers.Serializer):
    """Valida la FORMA de la petición. La legitimidad la decide el servicio."""

    token = serializers.CharField(max_length=512)
    nickname = serializers.CharField(max_length=32, allow_blank=True, required=False, default="")
    score = serializers.IntegerField(min_value=0, max_value=10_000_000, required=False, default=0)
    duration_ms = serializers.IntegerField(
        min_value=0, max_value=86_400_000, required=False, default=0
    )
    answers = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        required=False,
        default=list,
        max_length=100,
    )


class QuizResultSerializer(serializers.Serializer):
    """Respuesta tras enviar un cuestionario."""

    score = serializers.IntegerField()
    correct = serializers.IntegerField()
    total = serializers.IntegerField()
    nickname = serializers.CharField()
