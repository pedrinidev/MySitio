"""Hash de IP y tokens firmados: la base del anti-abuso del sitio."""

import pytest
from django.test import override_settings

from core.security import consume_signed_token, hash_ip, issue_signed_token

pytestmark = pytest.mark.django_db


def test_hash_ip_is_deterministic_and_irreversible():
    digest = hash_ip("190.104.1.5")
    assert digest == hash_ip("190.104.1.5")
    assert "190.104" not in digest
    assert len(digest) == 64


def test_different_ips_produce_different_hashes():
    assert hash_ip("1.1.1.1") != hash_ip("1.1.1.2")


def test_salt_changes_the_hash():
    """Cambiar la sal invalida cualquier tabla precomputada por un atacante."""
    with override_settings(IP_HASH_SALT="sal-uno"):
        first = hash_ip("1.1.1.1")
    with override_settings(IP_HASH_SALT="sal-dos"):
        second = hash_ip("1.1.1.1")
    assert first != second


def test_token_round_trip():
    token = issue_signed_token({"game": "snake"}, salt="test")
    payload = consume_signed_token(token, salt="test", max_age=60)
    assert payload is not None
    assert payload["game"] == "snake"


def test_token_can_only_be_used_once():
    """Sin esto, una puntuación válida podría reenviarse en bucle."""
    token = issue_signed_token({"game": "snake"}, salt="test")
    assert consume_signed_token(token, salt="test", max_age=60) is not None
    assert consume_signed_token(token, salt="test", max_age=60) is None


def test_tampered_token_is_rejected():
    token = issue_signed_token({"game": "snake"}, salt="test")
    assert consume_signed_token(token + "x", salt="test", max_age=60) is None


def test_token_from_another_salt_is_rejected():
    """Un token de sesión de juego no debe valer en otro contexto firmado."""
    token = issue_signed_token({"game": "snake"}, salt="games.session")
    assert consume_signed_token(token, salt="otra.cosa", max_age=60) is None


def test_expired_token_is_rejected():
    token = issue_signed_token({"game": "snake"}, salt="test")
    assert consume_signed_token(token, salt="test", max_age=-1) is None
