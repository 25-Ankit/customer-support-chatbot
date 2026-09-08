from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import (
    HashingError,
    VerificationError,
    VerifyMismatchError,
)


_password_hasher = PasswordHasher()


class PasswordSecurityError(Exception):
    """Base exception for password security operations."""


class PasswordHashingError(PasswordSecurityError):
    """Raised when password hashing fails."""


class PasswordVerificationError(PasswordSecurityError):
    """Raised when password verification cannot be performed."""


def hash_password(password: str) -> str:
    """Securely hash a user's password using Argon2."""

    if not isinstance(password, str):
        raise PasswordHashingError(
            "Password must be a string."
        )

    if not password:
        raise PasswordHashingError(
            "Password cannot be empty."
        )

    try:
        return _password_hasher.hash(password)

    except HashingError as error:
        raise PasswordHashingError(
            "Unable to securely hash the password."
        ) from error


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    """Verify a password against its Argon2 hash."""

    if not isinstance(password, str):
        return False

    if not isinstance(password_hash, str):
        return False

    if not password or not password_hash:
        return False

    try:
        return _password_hasher.verify(
            password_hash,
            password,
        )

    except VerifyMismatchError:
        return False

    except VerificationError:
        return False


def needs_rehash(password_hash: str) -> bool:
    """Check whether the stored hash should be upgraded."""

    if not isinstance(password_hash, str):
        return True

    if not password_hash:
        return True

    try:
        return _password_hasher.check_needs_rehash(
            password_hash
        )

    except (VerificationError, ValueError):
        return True
