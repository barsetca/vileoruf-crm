def normalize_email(email: str) -> str:
    """Normalize employee login identifiers at controlled input boundaries."""

    return email.strip().lower()
