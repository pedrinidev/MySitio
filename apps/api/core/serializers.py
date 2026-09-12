"""Piezas de serialización compartidas."""

from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from core.i18n import translate


class TranslatedField(serializers.Field):
    """Expone `campo_es` / `campo_en` como un único `campo`.

    Se declara explícitamente en cada serializador en vez de generarse por
    introspección. Es algo más verboso, pero al leer el serializador se ve
    exactamente qué campos salen y en qué forma — y eso vale más que
    ahorrarse tres líneas.

        class PostSerializer(serializers.ModelSerializer):
            title = TranslatedField()
    """

    def __init__(self, **kwargs) -> None:
        kwargs["source"] = "*"  # el campo necesita la instancia completa
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def to_representation(self, instance) -> str:
        language = self.context.get("lang", settings.DEFAULT_LANGUAGE)
        return translate(instance, self.field_name, language)

    def to_internal_value(self, data):  # pragma: no cover — el campo es de solo lectura
        raise NotImplementedError("TranslatedField es de solo lectura.")


class AbsoluteImageField(serializers.Field):
    """Devuelve la URL absoluta de una imagen, o None si no hay archivo.

    Un `ImageField` vacío devuelve cadena vacía, que en el frontend produce
    `<img src="">` — una petición extra al propio documento. None es explícito
    y el frontend puede decidir qué hacer.
    """

    def __init__(self, source_field: str, **kwargs) -> None:
        self.source_field = source_field
        kwargs["source"] = "*"
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def to_representation(self, instance) -> str | None:
        image = getattr(instance, self.source_field, None)
        if not image:
            return None

        # Con PUBLIC_MEDIA_BASE_URL definida manda esa, y no la cabecera Host
        # de quien pregunta. Hace falta en desarrollo con Docker: Astro pide
        # desde dentro de la red, así que el Host es «api:8000» y la URL
        # resultante apuntaba a un nombre que el navegador no resuelve — las
        # portadas salían rotas. En producción se deja vacía y vuelve a mandar
        # el Host, que allí ya es el dominio público.
        base = getattr(settings, "PUBLIC_MEDIA_BASE_URL", "")
        if base:
            return f"{base.rstrip('/')}{image.url}"

        request = self.context.get("request")
        return request.build_absolute_uri(image.url) if request else image.url
