from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.identity import normalize_email
from backend.app.core.security import hash_password
from backend.app.models import User, UserRole


class UserManagementError(ValueError):
    pass


class DuplicateEmailError(UserManagementError):
    pass


class UserNotFoundError(UserManagementError):
    pass


class AdminSafetyError(UserManagementError):
    pass


def normalize_display_name(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > 255:
        raise UserManagementError("Display name must be between 1 and 255 characters")
    return normalized


def list_users(session: Session) -> list[User]:
    return list(session.scalars(select(User).order_by(User.created_at, User.id)))


def create_user(session: Session, *, email: str, display_name: str, password: str, role: UserRole) -> User:
    normalized_email = normalize_email(email)
    if not normalized_email or len(normalized_email) > 320 or "@" not in normalized_email:
        raise UserManagementError("Invalid email")
    if session.scalar(select(User.id).where(User.email == normalized_email)) is not None:
        raise DuplicateEmailError
    user = User(email=normalized_email, display_name=normalize_display_name(display_name), password_hash=hash_password(password), role=role, is_active=True)
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise DuplicateEmailError from error
    session.refresh(user)
    return user


def update_user(session: Session, *, target_id: UUID, actor: User, changes: dict) -> User:
    session.execute(text("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"))
    target = session.get(User, target_id)
    if target is None:
        session.rollback()
        raise UserNotFoundError
    if target.id == actor.id and changes.get("is_active") is False:
        session.rollback()
        raise AdminSafetyError("You cannot deactivate your own account")
    if target.id == actor.id and changes.get("role") is UserRole.MANAGER:
        session.rollback()
        raise AdminSafetyError("You cannot remove your own administrator role")
    removes_active_admin = target.is_active and target.role is UserRole.ADMIN and (changes.get("is_active") is False or changes.get("role") is UserRole.MANAGER)
    if removes_active_admin:
        active_admins = session.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN, User.is_active.is_(True)))
        if active_admins <= 1:
            session.rollback()
            raise AdminSafetyError("At least one active administrator must remain")
    if "display_name" in changes:
        target.display_name = normalize_display_name(changes["display_name"])
    if "role" in changes:
        target.role = changes["role"]
    if "is_active" in changes:
        target.is_active = changes["is_active"]
    session.commit()
    session.refresh(target)
    return target
