"""QuantHub error types and their JSON envelope handler."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class HubError(Exception):
    """An HTTP-mapped QuantHub failure with a stable machine-readable code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "data": None,
            "error": {"code": self.code, "message": self.message},
        }
        if self.details:
            payload["error"]["details"] = self.details
        return payload


def not_found(message: str = "Project not found.") -> HubError:
    return HubError(404, "NotFound", message)


def forbidden(message: str = "You do not have permission to do that.") -> HubError:
    return HubError(403, "Forbidden", message)


def unauthorized(message: str = "Sign in to continue.") -> HubError:
    return HubError(401, "Unauthorized", message)


def bad_request(code: str, message: str, **details: Any) -> HubError:
    return HubError(400, code, message, details=details or None)


def conflict(code: str, message: str, **details: Any) -> HubError:
    return HubError(409, code, message, details=details or None)


async def hub_error_handler(request: Request, exc: HubError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())
