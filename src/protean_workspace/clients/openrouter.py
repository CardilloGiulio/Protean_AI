from typing import Any

import httpx

from protean_workspace.clients.provider import (
    CompletionResult,
    EmptyCompletionError,
    LengthCutoffError,
    ProviderError,
)
from protean_workspace.core.config import Settings


class OpenRouterError(ProviderError):
    pass


class OpenRouterClient:
    """Async OpenRouter transport. Credentials are supplied per request, never stored in the client."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.openrouter_base_url.rstrip("/"),
            timeout=settings.openrouter_timeout_seconds,
            headers={
                "Content-Type": "application/json",
                "HTTP-Referer": settings.openrouter_http_referer,
                "X-OpenRouter-Title": settings.app_name,
            },
        )
        # Capability fallback is cached per selected model for this process.
        # Once a router/model proves it cannot accept native json_schema, Protean
        # does not pay that compatibility failure again on every turn.
        self._structured_mode_by_model: dict[str, str] = {}

    async def close(self) -> None:
        await self._client.aclose()

    async def complete(
        self,
        *,
        api_key: str,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> CompletionResult:
        try:
            response = await self._client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._safe_error(exc.response)
            raise OpenRouterError(f"OpenRouter rejected the request: {detail}") from exc
        except httpx.HTTPError as exc:
            raise OpenRouterError("Could not reach OpenRouter") from exc
        return self._extract_completion(response.json())

    async def complete_structured(
        self,
        *,
        api_key: str,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any],
    ) -> CompletionResult:
        """Return JSON-shaped model output using the strongest supported mode.

        Preferred order:
        1. Native strict json_schema + require_parameters=true.
        2. json_object without strict provider capability routing.
        3. Plain completion, relying on Protean's JSON-only prompt + local validator.

        Only the specific OpenRouter "no compatible endpoint for requested
        parameters" routing failure triggers degradation. Auth, rate-limit,
        provider, and network errors are still surfaced normally.
        """

        mode_order = ["json_schema", "json_object", "plain_json"]
        cached_mode = self._structured_mode_by_model.get(model)
        if cached_mode in mode_order:
            modes = mode_order[mode_order.index(cached_mode):]
        else:
            modes = mode_order
        last_compatibility_error: httpx.HTTPStatusError | None = None

        for mode in modes:
            payload: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if mode == "json_schema":
                payload["response_format"] = response_format
                payload["provider"] = {"require_parameters": True}
            elif mode == "json_object":
                payload["response_format"] = {"type": "json_object"}

            try:
                response = await self._client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                compatibility_detail = self._compatibility_detail(exc.response)
                if mode != "plain_json" and self._is_structured_parameter_compatibility_error(
                    compatibility_detail
                ):
                    last_compatibility_error = exc
                    continue
                detail = self._safe_error(exc.response)
                raise OpenRouterError(f"OpenRouter rejected the structured request: {detail}") from exc
            except httpx.HTTPError as exc:
                raise OpenRouterError("Could not reach OpenRouter") from exc

            self._cache_structured_mode(model, mode)
            return self._extract_completion(response.json())

        # This is defensive: plain_json does not send structured-only parameters,
        # so a compatibility-only exhaustion should be unreachable.
        if last_compatibility_error is not None:
            detail = self._safe_error(last_compatibility_error.response)
            raise OpenRouterError(f"OpenRouter rejected the structured request: {detail}") from last_compatibility_error
        raise OpenRouterError("OpenRouter could not select a structured completion mode")

    def structured_mode_for_model(self, model: str) -> str | None:
        """Expose the in-process negotiated mode for diagnostics/tests only."""

        return self._structured_mode_by_model.get(model)

    def _cache_structured_mode(self, model: str, mode: str) -> None:
        if model not in self._structured_mode_by_model and len(self._structured_mode_by_model) >= 64:
            self._structured_mode_by_model.pop(next(iter(self._structured_mode_by_model)))
        self._structured_mode_by_model[model] = mode

    async def validate_key(self, api_key: str) -> dict[str, Any]:
        try:
            response = await self._client.get(
                "/key",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OpenRouterError(self._safe_error(exc.response)) from exc
        except httpx.HTTPError as exc:
            raise OpenRouterError("Could not reach OpenRouter") from exc
        data = response.json().get("data")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _extract_completion(data: dict[str, Any]) -> CompletionResult:
        try:
            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content")
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise OpenRouterError("OpenRouter response did not contain a completion") from exc

        # Some providers can return content blocks. Accept only visible text blocks;
        # never fall back to provider reasoning/thought fields.
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, str):
                    chunks.append(item)
                elif isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                    text = item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
            content = "".join(chunks)

        if not isinstance(content, str) or not content.strip():
            raise EmptyCompletionError("OpenRouter returned an empty completion")

        finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
        if str(finish_reason or "").lower() == "length":
            raise LengthCutoffError("OpenRouter stopped before the completion was finished")
        return CompletionResult(
            content=content.strip(),
            finish_reason=str(finish_reason) if finish_reason is not None else None,
        )

    @staticmethod
    def _is_structured_parameter_compatibility_error(detail: str) -> bool:
        normalized = " ".join(str(detail or "").lower().split())
        return (
            "no endpoints found that can handle the requested parameters" in normalized
            or ("no endpoints" in normalized and "requested parameters" in normalized)
        )

    @staticmethod
    def _safe_error(response: httpx.Response) -> str:
        # Provider bodies are untrusted and may echo credentials, bearer tokens,
        # prompts, or chat text. Never surface or log them.
        messages = {
            401: "authentication failed (HTTP 401)",
            403: "access was denied (HTTP 403)",
            429: "rate limit reached (HTTP 429)",
            500: "provider is unavailable (HTTP 500)",
            502: "provider is unavailable (HTTP 502)",
            503: "provider is unavailable (HTTP 503)",
            504: "provider timed out (HTTP 504)",
        }
        return messages.get(response.status_code, f"request failed (HTTP {response.status_code})")

    @staticmethod
    def _compatibility_detail(response: httpx.Response) -> str:
        """Read only the structured-routing signal; never return it to callers."""

        try:
            data = response.json()
        except ValueError:
            return ""
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"][:1000]
        return ""
