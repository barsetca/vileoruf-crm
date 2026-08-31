import getpass
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TextIO

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.identity import normalize_email
from backend.app.core.security import hash_password, validate_password
from backend.app.db.session import SessionLocal
from backend.app.models import User, UserRole


EMAIL_MAX_LENGTH = 320
DISPLAY_NAME_MAX_LENGTH = 255
SIMPLE_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AdminBootstrapError(ValueError):
    """Expected, safe-to-display bootstrap failure."""


@dataclass(frozen=True)
class AdminBootstrapInput:
    email: str
    display_name: str
    password: str


def validate_email(email: str) -> None:
    if len(email) > EMAIL_MAX_LENGTH or not SIMPLE_EMAIL_PATTERN.fullmatch(email):
        raise AdminBootstrapError("Enter a valid email address.")


def normalize_display_name(display_name: str) -> str:
    normalized = display_name.strip()
    if not normalized:
        raise AdminBootstrapError("Display name must not be empty.")
    if len(normalized) > DISPLAY_NAME_MAX_LENGTH:
        raise AdminBootstrapError(
            f"Display name must not exceed {DISPLAY_NAME_MAX_LENGTH} characters."
        )
    return normalized


def collect_admin_input(
    *,
    input_func: Callable[[str], str] = input,
    password_input: Callable[[str], str] | None = None,
) -> AdminBootstrapInput:
    hidden_input = password_input or getpass.getpass
    email = input_func("Email: ")
    display_name = input_func("Display name: ")
    password = hidden_input("Password: ")
    confirmation = hidden_input("Confirm password: ")

    if password != confirmation:
        raise AdminBootstrapError("Passwords do not match.")

    return AdminBootstrapInput(
        email=email,
        display_name=display_name,
        password=password,
    )


def create_first_admin(
    session: Session,
    *,
    email: str,
    display_name: str,
    password: str,
) -> User:
    try:
        normalized_email = normalize_email(email)
        validate_email(normalized_email)
        normalized_display_name = normalize_display_name(display_name)
        try:
            validate_password(password)
        except ValueError as error:
            raise AdminBootstrapError(str(error)) from error

        session.execute(text("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"))

        existing_admin_id = session.scalar(
            select(User.id).where(User.role == UserRole.ADMIN).limit(1)
        )
        if existing_admin_id is not None:
            raise AdminBootstrapError(
                "An ADMIN already exists; repeated bootstrap is not allowed."
            )

        existing_user_id = session.scalar(
            select(User.id).where(User.email == normalized_email).limit(1)
        )
        if existing_user_id is not None:
            raise AdminBootstrapError("A User with this email already exists.")

        admin = User(
            email=normalized_email,
            display_name=normalized_display_name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return admin
    except AdminBootstrapError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise AdminBootstrapError(
            "Database operation failed; ADMIN was not created."
        ) from error


def main(
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    input_func: Callable[[str], str] = input,
    password_input: Callable[[str], str] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    try:
        values = collect_admin_input(
            input_func=input_func,
            password_input=password_input,
        )
        with session_factory() as session:
            admin = create_first_admin(
                session,
                email=values.email,
                display_name=values.display_name,
                password=values.password,
            )
    except (EOFError, KeyboardInterrupt):
        print("ADMIN creation cancelled.", file=stderr)
        return 1
    except AdminBootstrapError as error:
        print(f"ADMIN creation failed: {error}", file=stderr)
        return 1

    print("ADMIN created successfully.", file=stdout)
    print(f"Email: {admin.email}", file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
