from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, JsonValue

from backend.app.models import AIErrorCategory


ResultT = TypeVar("ResultT", bound=BaseModel)


class StructuredProviderRequest(BaseModel):
    """Keeps application instructions separate from untrusted CRM data."""

    model_config = ConfigDict(extra="forbid")

    model: str
    trusted_instructions: str
    untrusted_business_data: dict[str, JsonValue]


@dataclass(frozen=True)
class ProviderResult(Generic[ResultT]):
    result: ResultT | dict[str, Any]
    actual_model: str
    usage: dict[str, int] | None = None


class ProviderFailure(RuntimeError):
    def __init__(
        self,
        category: AIErrorCategory,
        *,
        retryable: bool,
        actual_model: str | None = None,
        usage: dict[str, int] | None = None,
    ) -> None:
        super().__init__(category.value)
        self.category = category
        self.retryable = retryable
        self.actual_model = actual_model
        self.usage = usage


class AIProvider(Protocol):
    def generate_structured(
        self,
        request: StructuredProviderRequest,
        response_model: type[ResultT],
    ) -> ProviderResult[ResultT]: ...
