"""El aplanado bilingüe es transversal: si falla, falla todo el sitio en inglés."""

import pytest

from core.i18n import normalize_language, translate


class _Dummy:
    title_es = "Hola"
    title_en = "Hello"
    empty_es = "Solo español"
    empty_en = ""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("es", "es"),
        ("en", "en"),
        ("EN", "en"),
        ("en-US", "en"),
        (None, "es"),
        ("", "es"),
        ("fr", "es"),
        ("'; DROP TABLE--", "es"),
    ],
)
def test_normalize_language_never_trusts_input(raw, expected):
    """Un ?lang= manipulado devuelve el idioma por defecto, nunca un error."""
    assert normalize_language(raw) == expected


def test_translate_returns_requested_language():
    assert translate(_Dummy(), "title", "en") == "Hello"


def test_translate_falls_back_when_translation_is_empty():
    """Una traducción vacía muestra el español, no un hueco en blanco."""
    assert translate(_Dummy(), "empty", "en") == "Solo español"


def test_translate_returns_empty_string_for_unknown_field():
    assert translate(_Dummy(), "inexistente", "es") == ""
