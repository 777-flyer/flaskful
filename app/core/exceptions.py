"""Custom application exceptions for standardized REST API error responses."""

from __future__ import annotations

from typing import Any


class APIError(Exception):
    """Base exception for application-level API errors."""

    status_code: int = 400
    error_code: str = "BAD_REQUEST"
    message: str = "An error occurred while processing the request."

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message or self.message)
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.details = details or {}

    def to_dict(self, request_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": "error",
            "code": self.status_code,
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        if request_id:
            payload["request_id"] = request_id
        return payload


class NotFoundError(APIError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    error_code = "NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(APIError):
    """Raised when a resource state conflict occurs (e.g., duplicate email)."""

    status_code = 409
    error_code = "CONFLICT"
    message = "Resource conflict."


class UnauthorizedError(APIError):
    """Raised when authentication fails or credentials are invalid."""

    status_code = 401
    error_code = "UNAUTHORIZED"
    message = "Invalid or missing authentication credentials."


class ForbiddenError(APIError):
    """Raised when an authenticated user lacks permission for an action."""

    status_code = 403
    error_code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class AccountLockedError(APIError):
    """Raised when an account is temporarily locked due to brute-force attempts."""

    status_code = 423
    error_code = "ACCOUNT_LOCKED"
    message = "Account is temporarily locked due to multiple failed login attempts."
