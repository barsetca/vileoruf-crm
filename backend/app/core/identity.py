def normalize_email(email: str | None) -> str | None:
    """Return the canonical CRM email identity, or None for an absent value."""

    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized or None
