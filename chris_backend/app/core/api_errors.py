from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ApiError(Exception):
    """
    A domain-level API error that should be returned to clients in a consistent shape.

    Contract
    --------
    Inputs:
        - status_code: HTTP status to return (e.g., 400, 503)
        - code: stable machine-readable string (e.g., "model_a_unavailable")
        - message: human-readable message safe to show in UI
        - details: optional structured details for debugging (safe to expose)

    Output:
        - Raised exception handled by global exception handlers.

    Errors:
        - Not applicable (this is the error type itself).

    Side effects:
        - None.
    """

    status_code: int
    code: str
    message: str
    details: Any | None = None

    def __str__(self) -> str:  # pragma: no cover (trivial)
        base = f"{self.code}: {self.message}"
        return base if self.details is None else f"{base} ({self.details})"


class ModelUnavailableError(ApiError):
    """Raised when a requested model is not loaded/available for inference."""


class InvalidInputError(ApiError):
    """Raised when request payload or file input is invalid for the inference flow."""
