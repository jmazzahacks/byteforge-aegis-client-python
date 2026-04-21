"""Exceptions for the Aegis API client."""


class AegisError(Exception):
    """Base exception for all Aegis client errors."""


class AegisApiError(AegisError):
    """
    Raised when the API returns an error response (non-2xx).

    Attributes:
        status_code: HTTP status code
        message: Error message from the API
    """

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class AegisUnauthorized(AegisApiError):
    """
    Raised when the API returns 401 (missing/invalid/expired credentials).

    Subclass of AegisApiError, so existing `except AegisApiError` handlers
    still catch it. Callers that want to distinguish "not authenticated" from
    other API errors can catch this specifically.
    """

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(401, message)


class AegisNetworkError(AegisError):
    """
    Raised when a network/connection error occurs.

    Attributes:
        message: Description of the network error
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f"Network error: {message}")
