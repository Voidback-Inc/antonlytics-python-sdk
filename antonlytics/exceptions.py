"""
Antonlytics SDK — Exception hierarchy.

All SDK exceptions inherit from AntoError so callers can catch everything
with a single except clause, or be granular when needed.
"""
from __future__ import annotations

from typing import Any


class AntoError(Exception):
    """Base exception for all Antonlytics SDK errors."""

    def __init__(
        self,
        message: str,
        *,
        status: int = 0,
        code: str = "UNKNOWN",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.details = details

    def __repr__(self) -> str:
        return f"AntoError(code={self.code!r}, status={self.status}, message={self.message!r})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


class AuthenticationError(AntoError):
    """Raised on 401 — invalid or missing API key."""

    def __init__(self, message: str = "Invalid or missing API key.", **kwargs: Any) -> None:
        super().__init__(message, status=401, code="UNAUTHORIZED", **kwargs)


class PermissionError(AntoError):  # noqa: A001
    """Raised on 403 — API key lacks permission."""

    def __init__(self, message: str = "Permission denied.", **kwargs: Any) -> None:
        super().__init__(message, status=403, code="FORBIDDEN", **kwargs)


class NotFoundError(AntoError):
    """Raised on 404 — resource not found."""

    def __init__(self, message: str = "Resource not found.", **kwargs: Any) -> None:
        super().__init__(message, status=404, code="NOT_FOUND", **kwargs)


class PlanLimitError(AntoError):
    """Raised on 402 — event or API key quota exhausted for the current plan."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, status=402, code="PLAN_LIMIT_REACHED", **kwargs)


class ValidationError(AntoError):
    """Raised on 400/422 — invalid request payload."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, status=400, code="VALIDATION_ERROR", **kwargs)


class RateLimitError(AntoError):
    """Raised on 429 — too many requests."""

    def __init__(self, message: str = "Rate limit exceeded.", **kwargs: Any) -> None:
        super().__init__(message, status=429, code="RATE_LIMITED", **kwargs)


class ServerError(AntoError):
    """Raised on 5xx — backend error."""

    def __init__(self, message: str = "Internal server error.", **kwargs: Any) -> None:
        super().__init__(message, status=500, code="SERVER_ERROR", **kwargs)


class NetworkError(AntoError):
    """Raised when the request never reaches the server (DNS, connection refused, etc.)."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, status=0, code="NETWORK_ERROR", **kwargs)


class TimeoutError(AntoError):  # noqa: A001
    """Raised when the request exceeds the configured timeout."""

    def __init__(self, timeout: float) -> None:
        super().__init__(
            f"Request timed out after {timeout}s.",
            status=0,
            code="TIMEOUT",
        )
        self.timeout = timeout


class IngestionFailedError(AntoError):
    """Raised when an async ingestion job transitions to 'failed'."""

    def __init__(self, event_id: str, message: str) -> None:
        super().__init__(message, status=500, code="INGESTION_FAILED")
        self.event_id = event_id


class PollTimeoutError(AntoError):
    """Raised when polling an async ingestion event exceeds the timeout."""

    def __init__(self, event_id: str, timeout: float) -> None:
        super().__init__(
            f"Ingestion event {event_id} did not complete within {timeout}s.",
            status=0,
            code="POLL_TIMEOUT",
        )
        self.event_id = event_id


class InvalidConfigError(AntoError):
    """Raised when the client is misconfigured."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status=0, code="INVALID_CONFIG")


# ── Status code → exception class ─────────────────────────────────────────────

_STATUS_MAP: dict[int, type[AntoError]] = {
    400: ValidationError,
    401: AuthenticationError,
    402: PlanLimitError,
    403: PermissionError,
    404: NotFoundError,
    422: ValidationError,
    429: RateLimitError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
    504: ServerError,
}


def error_from_response(status: int, body: dict[str, Any]) -> AntoError:
    """Build the most specific AntoError subclass from an HTTP error response."""
    message = (
        body.get("detail")
        or body.get("message")
        or body.get("error", {}).get("detail")
        or f"HTTP {status}"
    )
    code = body.get("code") or body.get("error", {}).get("code") or ""
    cls = _STATUS_MAP.get(status, AntoError)

    # Special-case the plan limit 402 which has a specific code
    if status == 402 and code == "PLAN_LIMIT_REACHED":
        return PlanLimitError(message, details=body)

    err = cls(message, details=body)
    if code:
        err.code = code
    return err
