import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


_UNSAFE_SNAPSHOT_KEYS = {
    "body",
    "communication",
    "communications",
    "content",
    "description",
    "messages",
    "prompt",
    "raw_prompt",
    "raw_provider_request",
    "raw_provider_response",
    "raw_request",
    "raw_response",
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
}


class InvalidFingerprintInputError(ValueError):
    pass


def deterministic_input_fingerprint(payload: dict[str, Any]) -> str:
    normalized = _normalize_json_value(payload)
    try:
        serialized = json.dumps(
            normalized,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise InvalidFingerprintInputError from error
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_compact_snapshot(
    source: dict[str, Any],
    *,
    include_fields: tuple[str, ...],
    max_string_length: int = 256,
    max_collection_items: int = 25,
    max_depth: int = 4,
) -> dict[str, Any]:
    """Copy only explicitly selected, compact, non-free-text audit fields."""

    snapshot: dict[str, Any] = {}
    for key in include_fields:
        if key in source and not _is_unsafe_snapshot_key(key):
            snapshot[key] = _compact_value(
                source[key],
                depth=0,
                max_depth=max_depth,
                max_string_length=max_string_length,
                max_collection_items=max_collection_items,
            )
    return snapshot


def _normalize_json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _normalize_json_value(value.model_dump(mode="json"))
    if isinstance(value, Enum):
        return _normalize_json_value(value.value)
    if isinstance(value, (UUID, date, datetime, Decimal)):
        return str(value)
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise InvalidFingerprintInputError("Fingerprint object keys must be strings")
        return {key: _normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise InvalidFingerprintInputError(
        f"Unsupported fingerprint value type: {type(value).__name__}"
    )


def _compact_value(
    value: Any,
    *,
    depth: int,
    max_depth: int,
    max_string_length: int,
    max_collection_items: int,
) -> Any:
    if depth >= max_depth:
        return "[truncated]"
    normalized = _normalize_json_value(value)
    if isinstance(normalized, str):
        return normalized[:max_string_length]
    if isinstance(normalized, dict):
        return {
            key: _compact_value(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_string_length=max_string_length,
                max_collection_items=max_collection_items,
            )
            for key, item in list(normalized.items())[:max_collection_items]
            if not _is_unsafe_snapshot_key(key)
        }
    if isinstance(normalized, list):
        return [
            _compact_value(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_string_length=max_string_length,
                max_collection_items=max_collection_items,
            )
            for item in normalized[:max_collection_items]
        ]
    return normalized


def _is_unsafe_snapshot_key(key: str) -> bool:
    normalized = key.lower()
    return (
        normalized in _UNSAFE_SNAPSHOT_KEYS
        or normalized.endswith("_description")
        or "communication" in normalized
        or "prompt" in normalized
        or normalized.startswith("raw_")
        or normalized.endswith("_token")
        or normalized.endswith("_secret")
        or normalized.endswith("_password")
        or normalized.endswith("_api_key")
    )
