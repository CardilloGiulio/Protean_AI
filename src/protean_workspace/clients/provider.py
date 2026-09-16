from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class CompletionResult:
    content: str
    finish_reason: str | None = None


class ProviderError(RuntimeError):
    pass


class EmptyCompletionError(ProviderError):
    """The provider returned no usable visible completion content."""


class LengthCutoffError(ProviderError):
    """The provider stopped because the output ceiling was reached."""


class ChatProvider(Protocol):
    async def complete(
        self,
        *,
        api_key: str,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> CompletionResult: ...

    async def complete_structured(
        self,
        *,
        api_key: str,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any],
    ) -> CompletionResult: ...

    async def validate_key(self, api_key: str) -> dict[str, Any]: ...
