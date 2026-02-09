"""Custom exception classes for Git Phantom Scope.

All exceptions follow the GPS error format:
{
    "error": {
        "code": "GPS_ERROR_CODE",
        "message": "Human-readable message",
        "details": {}  # optional
    }
}

CRITICAL: Error messages must NEVER contain PII (usernames, emails, keys).
"""

from __future__ import annotations

from typing import Any


class GPSBaseError(Exception):
    """Base exception for Git Phantom Scope."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result


class ExternalServiceError(GPSBaseError):
    """External service (GitHub, AI model) unavailable."""

    def __init__(self, service: str, message: str = "Service unavailable") -> None:
        super().__init__(
            code=f"{service.upper()}_SERVICE_ERROR",
            message=message,
            status_code=502,
        )


class GitHubAPIError(GPSBaseError):
    """GitHub API specific errors."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(
            code="GITHUB_API_ERROR",
            message=message,
            status_code=status_code,
        )


class GitHubUserNotFoundError(GPSBaseError):
    """GitHub user not found."""

    def __init__(self) -> None:
        super().__init__(
            code="GITHUB_USER_NOT_FOUND",
            message="GitHub user not found",
            status_code=404,
        )


class GitHubRateLimitError(GPSBaseError):
    """GitHub API rate limit exceeded."""

    def __init__(self, retry_after: int | None = None) -> None:
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(
            code="GITHUB_RATE_LIMIT",
            message="GitHub API rate limit exceeded. Try again later.",
            status_code=429,
            details=details,
        )


class RateLimitError(GPSBaseError):
    """Application rate limit exceeded."""

    def __init__(self, limit_type: str, retry_after: int = 60) -> None:
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded for {limit_type}. Try again later.",
            status_code=429,
            details={"retry_after_seconds": retry_after, "limit_type": limit_type},
        )


class SessionNotFoundError(GPSBaseError):
    """Session expired or not found."""

    def __init__(self) -> None:
        super().__init__(
            code="SESSION_NOT_FOUND",
            message="Session not found or expired. Please start a new analysis.",
            status_code=404,
        )


class InvalidBYOKKeyError(GPSBaseError):
    """BYOK key validation failed."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            code="INVALID_BYOK_KEY",
            message=f"Invalid API key for provider: {provider}",
            status_code=401,
        )


class GenerationError(GPSBaseError):
    """Asset generation failed."""

    def __init__(self, message: str = "Generation failed") -> None:
        super().__init__(
            code="GENERATION_FAILED",
            message=message,
            status_code=500,
        )


class ModelProviderError(GPSBaseError):
    """AI model provider error."""

    def __init__(self, provider: str, message: str = "Model call failed") -> None:
        super().__init__(
            code="MODEL_PROVIDER_ERROR",
            message=message,
            status_code=502,
            details={"provider": provider},
        )


class ValidationError(GPSBaseError):
    """Input validation error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            details=details,
        )
