from __future__ import annotations

import pytest

from sentinela.security import (
    InvalidToken,
    hash_password,
    issue_token,
    verify_password,
    verify_token,
)


def test_scrypt_password_hash_and_wrong_password():
    encoded = hash_password("correct synthetic passphrase")
    assert encoded.startswith("scrypt$")
    assert verify_password("correct synthetic passphrase", encoded)
    assert not verify_password("incorrect passphrase", encoded)


def test_token_signature_subject_and_expiry():
    secret = "S" * 48
    token = issue_token(42, secret, lifetime_seconds=60)
    assert verify_token(token, secret) == 42
    with pytest.raises(InvalidToken):
        verify_token(token, "X" * 48)
    expired = issue_token(42, secret, lifetime_seconds=-1)
    with pytest.raises(InvalidToken):
        verify_token(expired, secret)
