from io import StringIO
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.security import verify_password
from backend.app.models import User, UserRole
from backend.app.scripts.create_admin import (
    AdminBootstrapError,
    collect_admin_input,
    create_first_admin,
    main,
    normalize_email,
    validate_email,
)


VALID_PASSWORD = "synthetic bootstrap password"


class FakeSession:
    def __init__(
        self,
        scalar_results: list[object | None] | None = None,
        *,
        commit_error: SQLAlchemyError | None = None,
    ) -> None:
        self.scalar_results = list(scalar_results or [None, None])
        self.commit_error = commit_error
        self.added = []
        self.commit_count = 0
        self.rollback_count = 0
        self.execute_count = 0

    def execute(self, statement) -> None:
        self.execute_count += 1

    def scalar(self, statement):
        return self.scalar_results.pop(0)

    def add(self, value) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.commit_count += 1
        if self.commit_error is not None:
            raise self.commit_error

    def refresh(self, value) -> None:
        if value.id is None:
            value.id = uuid4()

    def rollback(self) -> None:
        self.rollback_count += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None


def test_successful_admin_creation_normalizes_and_hashes() -> None:
    session = FakeSession()

    admin = create_first_admin(
        session,
        email="  Admin@Example.COM  ",
        display_name="  Studio Administrator  ",
        password=VALID_PASSWORD,
    )

    assert admin.email == "admin@example.com"
    assert admin.display_name == "Studio Administrator"
    assert admin.role is UserRole.ADMIN
    assert admin.is_active is True
    assert admin.password_hash != VALID_PASSWORD
    assert admin.password_hash.startswith("$argon2id$")
    assert verify_password(VALID_PASSWORD, admin.password_hash)
    assert not hasattr(admin, "password")
    assert session.added == [admin]
    assert session.commit_count == 1
    assert session.rollback_count == 0


@pytest.mark.parametrize("email", ["", "not-an-email", "user@localhost", "a" * 321])
def test_invalid_email_is_rejected(email: str) -> None:
    with pytest.raises(AdminBootstrapError, match="valid email"):
        validate_email(normalize_email(email))


@pytest.mark.parametrize("display_name", ["", "   ", "x" * 256])
def test_invalid_display_name_creates_no_user(display_name: str) -> None:
    session = FakeSession()

    with pytest.raises(AdminBootstrapError):
        create_first_admin(
            session,
            email="admin@example.test",
            display_name=display_name,
            password=VALID_PASSWORD,
        )

    assert session.added == []
    assert session.commit_count == 0
    assert session.rollback_count == 1


@pytest.mark.parametrize("password", ["x" * 11, "x" * 129])
def test_existing_password_policy_is_enforced(password: str) -> None:
    session = FakeSession()

    with pytest.raises(AdminBootstrapError, match="Password length"):
        create_first_admin(
            session,
            email="admin@example.test",
            display_name="Administrator",
            password=password,
        )

    assert session.added == []
    assert session.commit_count == 0


def test_duplicate_normalized_email_is_rejected_without_changes() -> None:
    existing_user = User(
        id=uuid4(),
        email="admin@example.com",
        password_hash="$argon2id$unchanged",
        display_name="Existing Manager",
        role=UserRole.MANAGER,
        is_active=False,
    )
    session = FakeSession([None, existing_user.id])

    with pytest.raises(AdminBootstrapError, match="email already exists"):
        create_first_admin(
            session,
            email="  Admin@Example.COM ",
            display_name="Administrator",
            password=VALID_PASSWORD,
        )

    assert session.added == []
    assert session.commit_count == 0
    assert session.rollback_count == 1
    assert existing_user.role is UserRole.MANAGER
    assert existing_user.is_active is False
    assert existing_user.password_hash == "$argon2id$unchanged"


def test_any_existing_admin_blocks_repeated_bootstrap() -> None:
    session = FakeSession([uuid4()])

    with pytest.raises(AdminBootstrapError, match="ADMIN already exists"):
        create_first_admin(
            session,
            email="second-admin@example.test",
            display_name="Second Administrator",
            password=VALID_PASSWORD,
        )

    assert session.added == []
    assert session.commit_count == 0
    assert session.rollback_count == 1


def test_inactive_admin_also_blocks_repeated_bootstrap() -> None:
    session = FakeSession([uuid4()])

    with pytest.raises(AdminBootstrapError, match="ADMIN already exists"):
        create_first_admin(
            session,
            email="replacement-admin@example.test",
            display_name="Replacement Administrator",
            password=VALID_PASSWORD,
        )

    assert session.added == []
    assert session.commit_count == 0
    assert session.rollback_count == 1


def test_bootstrap_acquires_transaction_lock_before_user_checks() -> None:
    session = FakeSession()

    create_first_admin(
        session,
        email="admin@example.test",
        display_name="Administrator",
        password=VALID_PASSWORD,
    )

    assert session.execute_count == 1


def test_database_error_rolls_back_and_uses_safe_error() -> None:
    session = FakeSession(commit_error=SQLAlchemyError("sensitive DB detail"))

    with pytest.raises(AdminBootstrapError) as error:
        create_first_admin(
            session,
            email="admin@example.test",
            display_name="Administrator",
            password=VALID_PASSWORD,
        )

    assert str(error.value) == "Database operation failed; ADMIN was not created."
    assert "sensitive" not in str(error.value)
    assert session.rollback_count == 1


def test_collect_admin_input_uses_hidden_password_input() -> None:
    ordinary_prompts = []
    secret_prompts = []
    ordinary_values = iter(["admin@example.test", "Administrator"])
    secret_values = iter([VALID_PASSWORD, VALID_PASSWORD])

    values = collect_admin_input(
        input_func=lambda prompt: (
            ordinary_prompts.append(prompt) or next(ordinary_values)
        ),
        password_input=lambda prompt: (
            secret_prompts.append(prompt) or next(secret_values)
        ),
    )

    assert values.password == VALID_PASSWORD
    assert ordinary_prompts == ["Email: ", "Display name: "]
    assert secret_prompts == ["Password: ", "Confirm password: "]


def test_password_confirmation_mismatch_fails_before_database_access() -> None:
    session_factory_called = False

    def forbidden_session_factory():
        nonlocal session_factory_called
        session_factory_called = True
        raise AssertionError("Database must not be accessed")

    stderr = StringIO()
    ordinary_values = iter(["admin@example.test", "Administrator"])
    secret_values = iter([VALID_PASSWORD, "different password"])
    exit_code = main(
        session_factory=forbidden_session_factory,
        input_func=lambda prompt: next(ordinary_values),
        password_input=lambda prompt: next(secret_values),
        stderr=stderr,
    )

    assert exit_code == 1
    assert "Passwords do not match" in stderr.getvalue()
    assert session_factory_called is False


def test_main_success_output_contains_no_password_or_hash() -> None:
    session = FakeSession()
    stdout = StringIO()
    ordinary_values = iter([" Admin@Example.TEST ", " Administrator "])
    secret_values = iter([VALID_PASSWORD, VALID_PASSWORD])

    exit_code = main(
        session_factory=lambda: session,
        input_func=lambda prompt: next(ordinary_values),
        password_input=lambda prompt: next(secret_values),
        stdout=stdout,
    )

    output = stdout.getvalue()
    assert exit_code == 0
    assert "ADMIN created successfully." in output
    assert "Email: admin@example.test" in output
    assert VALID_PASSWORD not in output
    assert "$argon2" not in output
