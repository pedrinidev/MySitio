from __future__ import annotations

from rest_framework import serializers

from modules.contact.models import ContactMessage


class ContactMessageSerializer(serializers.ModelSerializer):
    """Entrada del formulario, con las dos trampas anti-bot.

    Ninguna de las dos molesta a una persona real: el honeypot es invisible y
    el tiempo transcurrido lo mide el propio formulario.
    """

    # Campo señuelo: oculto por CSS. Un humano no lo ve; un bot que rellena
    # todo lo que encuentra en el DOM, sí.
    website = serializers.CharField(required=False, allow_blank=True, default="")
    # Milisegundos entre que se pintó el formulario y se envió.
    elapsed_ms = serializers.IntegerField(required=False, default=0, min_value=0)

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "subject", "message", "locale", "website", "elapsed_ms")
        extra_kwargs = {
            "name": {"min_length": 2, "max_length": 120},
            "subject": {"min_length": 3, "max_length": 200},
            "message": {"min_length": 10, "max_length": 5000},
        }

    def validate_locale(self, value: str) -> str:
        return value if value in ("es", "en") else "es"

    def validate_message(self, value: str) -> str:
        """Rechaza el patrón más común de spam: un muro de enlaces."""
        if value.lower().count("http") > 5:
            raise serializers.ValidationError("El mensaje contiene demasiados enlaces.")
        return value
