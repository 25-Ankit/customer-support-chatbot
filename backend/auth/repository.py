from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from backend.auth.models import (
    User,
    UserRole,
    normalize_email,
)


class UserRepositoryError(Exception):
    """Base exception for user repository operations."""


class UserAlreadyExistsError(UserRepositoryError):
    """Raised when a user with the same email already exists."""


class UserNotFoundError(UserRepositoryError):
    """Raised when a requested user does not exist."""


class UserRepository:
    """Persistence layer for application users."""

    def __init__(self, database_path: str):
        if not isinstance(database_path, str) or not database_path.strip():
            raise ValueError("Database path must be a non-empty string.")

        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row

        connection.execute("PRAGMA foreign_keys = ON")

        return connection

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        """Convert a database row into a User model."""

        return User(
            id=int(row["id"]),
            email=row["email"],
            password_hash=row["password_hash"],
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(
                row["created_at"]
            ),
        )

    def create_user(
        self,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.CUSTOMER,
    ) -> User:
        """Create and persist a new user."""

        email = normalize_email(email)

        if not isinstance(password_hash, str) or not password_hash:
            raise ValueError(
                "Password hash must be a non-empty string."
            )

        if not isinstance(role, UserRole):
            try:
                role = UserRole(str(role).strip().lower())
            except ValueError as error:
                raise ValueError(
                    f"Invalid user role: {role!r}"
                ) from error

        created_at = datetime.now(timezone.utc)

        connection = self._connect()

        try:
            cursor = connection.execute(
                """
                INSERT INTO users (
                    email,
                    password_hash,
                    role,
                    is_active,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    email,
                    password_hash,
                    role.value,
                    1,
                    created_at.isoformat(),
                ),
            )

            user_id = cursor.lastrowid

            if user_id is None:
                raise UserRepositoryError(
                    "Unable to determine the new user's ID."
                )

            connection.commit()

            return User(
                id=int(user_id),
                email=email,
                password_hash=password_hash,
                role=role,
                is_active=True,
                created_at=created_at,
            )

        except sqlite3.IntegrityError as error:
            connection.rollback()

            if "users.email" in str(error).lower():
                raise UserAlreadyExistsError(
                    "A user with this email already exists."
                ) from error

            raise UserRepositoryError(
                "User could not be created because of a database constraint."
            ) from error

        except sqlite3.Error as error:
            connection.rollback()

            raise UserRepositoryError(
                "Unable to create user."
            ) from error

        finally:
            connection.close()

    def get_user_by_email(
        self,
        email: str,
    ) -> User | None:
        """Find a user by normalized email address."""

        email = normalize_email(email)

        connection = self._connect()

        try:
            row = connection.execute(
                """
                SELECT
                    id,
                    email,
                    password_hash,
                    role,
                    is_active,
                    created_at
                FROM users
                WHERE email = ?
                LIMIT 1
                """,
                (email,),
            ).fetchone()

            if row is None:
                return None

            return self._row_to_user(row)

        except sqlite3.Error as error:
            raise UserRepositoryError(
                "Unable to retrieve user."
            ) from error

        finally:
            connection.close()

    def get_user_by_id(
        self,
        user_id: int,
    ) -> User | None:
        """Find a user by their database ID."""

        if isinstance(user_id, bool) or not isinstance(user_id, int):
            raise ValueError("User ID must be an integer.")

        if user_id < 1:
            raise ValueError("User ID must be greater than zero.")

        connection = self._connect()

        try:
            row = connection.execute(
                """
                SELECT
                    id,
                    email,
                    password_hash,
                    role,
                    is_active,
                    created_at
                FROM users
                WHERE id = ?
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

            if row is None:
                return None

            return self._row_to_user(row)

        except sqlite3.Error as error:
            raise UserRepositoryError(
                "Unable to retrieve user."
            ) from error

        finally:
            connection.close()

    def user_exists(self, email: str) -> bool:
        """Check whether an account already exists."""

        email = normalize_email(email)

        connection = self._connect()

        try:
            row = connection.execute(
                """
                SELECT 1
                FROM users
                WHERE email = ?
                LIMIT 1
                """,
                (email,),
            ).fetchone()

            return row is not None

        except sqlite3.Error as error:
            raise UserRepositoryError(
                "Unable to check whether the user exists."
            ) from error

        finally:
            connection.close()
