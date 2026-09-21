"""Shared remote model client.

Every specialist model (GeoChat, ChangeFormer, Prithvi, SARMAE, TerraMind)
calls its hosted inference endpoint through a subclass of
``RemoteModelClient``.  This module provides:

- A reusable async HTTP client with configurable timeout
- Structured error types that map to ``Observation`` statuses
- Security: API keys are never logged, traced, or included in errors
- Graceful handling of empty/unconfigured endpoints
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Error hierarchy
# ------------------------------------------------------------------

class RemoteModelError(Exception):
    """Base for all remote-model client errors."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class EndpointNotConfiguredError(RemoteModelError):
    """Raised when the endpoint URL is empty / not set in .env."""

    def __init__(self, model_name: str) -> None:
        super().__init__(
            f"{model_name} endpoint is not configured. "
            f"Set the endpoint URL in .env to enable this capability.",
            retryable=False,
        )


class ModelTimeoutError(RemoteModelError):
    """Remote model did not respond within the configured timeout."""

    def __init__(self, model_name: str, timeout: float) -> None:
        super().__init__(
            f"{model_name} inference timed out after {timeout}s.",
            retryable=True,
        )


class ModelConnectionError(RemoteModelError):
    """Could not establish a connection to the remote model."""

    def __init__(self, model_name: str, detail: str = "") -> None:
        super().__init__(
            f"Connection to {model_name} endpoint failed"
            + (f": {detail}" if detail else "."),
            retryable=True,
        )


class ModelAuthError(RemoteModelError):
    """The remote endpoint rejected authentication (401/403)."""

    def __init__(self, model_name: str) -> None:
        super().__init__(
            f"{model_name} authentication failed. Check API key configuration.",
            retryable=False,
        )


class ModelResponseError(RemoteModelError):
    """The remote endpoint returned a non-success HTTP status or malformed body."""

    def __init__(self, model_name: str, status_code: int, detail: str = "") -> None:
        super().__init__(
            f"{model_name} returned HTTP {status_code}"
            + (f": {detail}" if detail else "."),
            retryable=(500 <= status_code < 600),
        )
        self.status_code = status_code


# ------------------------------------------------------------------
# Base client
# ------------------------------------------------------------------

class RemoteModelClient:
    """Reusable async HTTP client for calling hosted specialist models.

    Subclasses override ``_build_request`` and ``_parse_response``
    to translate between the SatQuery internal contract and the
    model-specific hosted API contract.

    Parameters
    ----------
    model_name:
        Human-readable name used in logs and error messages.
    endpoint:
        Base URL of the hosted model service.
    api_key:
        Optional bearer token / API key.
    timeout_seconds:
        Per-request timeout in seconds.
    """

    def __init__(
        self,
        *,
        model_name: str,
        endpoint: str,
        api_key: str = "",
        timeout_seconds: float = 60,
    ) -> None:
        self.model_name = model_name
        self.endpoint = endpoint.rstrip("/") if endpoint else ""
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def infer(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send *payload* to the remote model and return the parsed response.

        Raises one of the ``RemoteModelError`` subclasses on failure —
        the adapter converts these into ``Observation`` objects.
        """
        if not self.endpoint:
            raise EndpointNotConfiguredError(self.model_name)

        url, headers, body = self._build_request(payload)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException:
            raise ModelTimeoutError(self.model_name, self.timeout_seconds)
        except httpx.ConnectError as exc:
            raise ModelConnectionError(self.model_name, str(exc))
        except httpx.RequestError as exc:
            raise ModelConnectionError(self.model_name, str(exc))

        # Auth failures
        if response.status_code in (401, 403):
            raise ModelAuthError(self.model_name)

        # Other HTTP errors
        if response.status_code >= 400:
            detail = response.text[:500] if response.text else ""
            raise ModelResponseError(
                self.model_name, response.status_code, detail
            )

        # Parse JSON body
        try:
            raw_json = response.json()
        except Exception:
            raise ModelResponseError(
                self.model_name,
                response.status_code,
                "Response body is not valid JSON.",
            )

        return self._parse_response(raw_json)

    # ------------------------------------------------------------------
    # Extension points (override in subclasses)
    # ------------------------------------------------------------------

    def _build_request(
        self, payload: dict[str, Any]
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        """Return (url, headers, body) for the HTTP POST.

        Default implementation posts to ``{endpoint}/predict`` with
        an optional ``Authorization: Bearer`` header.
        Subclasses may override to target a different path or
        restructure the body for a specific hosted API.
        """
        url = f"{self.endpoint}/predict"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return url, headers, payload

    def _parse_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Extract the model result from the raw JSON response.

        Default implementation returns the JSON as-is.
        Subclasses may override to unwrap nested structures.
        """
        return raw
