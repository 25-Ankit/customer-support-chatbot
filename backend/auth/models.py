from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


# =========================================================
# Security Constants
# =========================================================

MIN_USER_ID = 1

MIN_EMAIL_LENGTH = 5
MAX_EMAIL_LENGTH = 254

MIN_PASSWORD_HASH_LENGTH = 20
MAX_PASSWORD_HASH_LENGTH = 255

EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


# =========================================================
# User Roles
# =========================================================

class UserRole(StrEnum):
    """
    Roles supported by the application.

    Using an enum prevents arbitrary strings such as:

        "superadmin"
        "root"
        "hacker"

    from being accidentally accepted as valid roles.
    """

    CUSTOMER = "customer"
    SUPPORT = "support"
    ADMIN = "admin"


# =========================================================
# Authentication Exceptions
# =========================================================

class UserModelError(ValueError):
    """
    Base exception for invalid user data.
    """


class InvalidUserIDError(UserModelError):
    """
    Raised when a user ID is invalid.
    """


class InvalidEmailError(UserModelError):
    """
    Raised when an email address is invalid.
    """


class InvalidPasswordHashError(UserModelError):
    """
    Raised when a password hash is invalid.
    """


class InvalidRoleError(UserModelError):
    """
    Raised when an unsupported role is supplied.
    """


# =========================================================
# Email Normalization
# =========================================================

def normalize_email(email: str) -> str:
    """
    Normalize an email address before storing or comparing it.

    Example:

        "  User@Example.COM  "

    becomes:

        "user@example.com"
    """

    if not isinstance(email, str):
        raise InvalidEmailError(
            "Email must be a string."
        )

    normalized = email.strip().lower()

    if not normalized:
        raise InvalidEmailError(
            "Email cannot be empty."
        )

    if len(normalized) < MIN_EMAIL_LENGTH:
        raise InvalidEmailError(
            "Email address is too short."
        )

    if len(normalized) > MAX_EMAIL_LENGTH:
        raise InvalidEmailError(
            "Email address is too long."
        )

    if not EMAIL_PATTERN.fullmatch(normalized):
        raise InvalidEmailError(
            "Invalid email address."
        )

    return normalized


# =========================================================
# User ID Validation
# =========================================================

def validate_user_id(user_id: int) -> int:
    """
    Validate a user identifier.

    Boolean values are explicitly rejected because Python
    considers bool to be a subclass of int.

    Without this check:

        True == 1

    could accidentally be accepted as a user ID.
    """

    if isinstance(user_id, bool):
        raise InvalidUserIDError(
            "User ID must be an integer."
        )

    if not isinstance(user_id, int):
        raise InvalidUserIDError(
            "User ID must be an integer."
        )

    if user_id < MIN_USER_ID:
        raise InvalidUserIDError(
            "User ID must be greater than zero."
        )

    return user_id


# =========================================================
# Password Hash Validation
# =========================================================

def validate_password_hash(password_hash: str) -> str:
    """
    Validate that the supplied value looks like a stored
    password hash.

    This function does NOT hash passwords.

    Password hashing will be implemented separately using
    a password-hashing algorithm such as Argon2.

    The model must never receive a plaintext password.
    """

    if not isinstance(password_hash, str):
        raise InvalidPasswordHashError(
            "Password hash must be a string."
        )

    password_hash = password_hash.strip()

    if not password_hash:
        raise InvalidPasswordHashError(
            "Password hash cannot be empty."
        )

    if len(password_hash) < MIN_PASSWORD_HASH_LENGTH:
        raise InvalidPasswordHashError(
            "Password hash is invalid."
        )

    if len(password_hash) > MAX_PASSWORD_HASH_LENGTH:
        raise InvalidPasswordHashError(
            "Password hash is too long."
        )

    return password_hash


# =========================================================
# Role Validation
# =========================================================

def validate_role(role: UserRole | str) -> UserRole:
    """
    Convert and validate a user role.

    Both are accepted:

        UserRole.CUSTOMER
        "customer"

    Anything else is rejected.
    """

    if isinstance(role, UserRole):
        return role

    if not isinstance(role, str):
        raise InvalidRoleError(
            "Role must be a valid UserRole."
        )

    try:
        return UserRole(role.strip().lower())

    except ValueError as error:
        raise InvalidRoleError(
            f"Unsupported user role: {role!r}"
        ) from error


# =========================================================
# Timestamp Validation
# =========================================================

def validate_created_at(
    created_at: datetime | None,
) -> datetime:
    """
    Validate and normalize the user creation timestamp.

    Naive timestamps are rejected because authentication
    systems should avoid ambiguous timezone handling.
    """

    if created_at is None:
        return datetime.now(timezone.utc)

    if not isinstance(created_at, datetime):
        raise UserModelError(
            "created_at must be a datetime."
        )

    if created_at.tzinfo is None:
        raise UserModelError(
            "created_at must be timezone-aware."
        )

    return created_at.astimezone(timezone.utc)


# =========================================================
# User Model
# =========================================================

@dataclass(slots=True)
class User:
    """
    Represents an authenticated application user.

    Security principles:

    - Never store plaintext passwords.
    - Normalize email addresses.
    - Restrict roles.
    - Validate identifiers.
    - Use timezone-aware UTC timestamps.
    - Keep authentication logic outside this model.

    The model is intentionally independent from the
    database layer so that we can later migrate from:

        SQLite → PostgreSQL + SQLAlchemy

    without coupling authentication to a specific database.
    """

    id: int
    email: str
    password_hash: str

    role: UserRole = UserRole.CUSTOMER

    is_active: bool = True

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        """
        Validate all user fields immediately after creation.
        """

        self.id = validate_user_id(self.id)

        self.email = normalize_email(self.email)

        self.password_hash = validate_password_hash(
            self.password_hash
        )

        self.role = validate_role(self.role)

        if not isinstance(self.is_active, bool):
            raise UserModelError(
                "is_active must be a boolean."
            )

        self.created_at = validate_created_at(
            self.created_at
        )

    # -----------------------------------------------------
    # Convenience Properties
    # -----------------------------------------------------

    @property
    def is_customer(self) -> bool:
        """Return True when the user is a customer."""

        return self.role == UserRole.CUSTOMER

    @property
    def is_support(self) -> bool:
        """Return True when the user is support staff."""

        return self.role == UserRole.SUPPORT

    @property
    def is_admin(self) -> bool:
        """Return True when the user is an administrator."""

        return self.role == UserRole.ADMIN

    # -----------------------------------------------------
    # Account State
    # -----------------------------------------------------

    def can_authenticate(self) -> bool:
        """
        Determine whether the account is currently allowed
        to authenticate.
        """

        return self.is_active
