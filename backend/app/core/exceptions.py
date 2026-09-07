"""Domain exceptions and their HTTP handlers.

Services raise these; the router layer never builds HTTP error responses by
hand. Every error is serialized to the uniform shape from architecture.md 7:

    {"error": {"code": "...", "message": "...", "details": ...}}

Messages are in Spanish (shown to the user); codes are in English (consumed by
the frontend).
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class DomainError(Exception):
    """Base class for business errors. Maps to an HTTP status and an error code.

    Each subclass sets a default code; a specific code (e.g. EMAIL_ALREADY_REGISTERED)
    may be supplied per instance so the frontend can distinguish cases that share
    the same HTTP status.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "DOMAIN_ERROR"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None) -> None:
        self.message = message
        self.details = details
        if code is not None:
            self.code = code
        super().__init__(message)


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class ForbiddenError(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


class ConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class ValidationError(DomainError):
    status_code = 422  # UNPROCESSABLE_CONTENT
    code = "VALIDATION_ERROR"


class AuthenticationError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHENTICATED"


def _error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(IntegrityError)
    async def _handle_integrity_error(_: Request, __: IntegrityError) -> JSONResponse:
        """Last line of defense for a constraint the service layer did not
        anticipate.

        Anything reaching here is a gap in validation and should be fixed there;
        this handler only makes sure the client gets the uniform error shape
        instead of a bare 500, and that the database message — which names
        tables, columns and row contents — never leaves the server. The session
        is discarded by ``get_db`` on the way out, so nothing half-written
        survives.
        """
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error_body(
                "CONSTRAINT_VIOLATION",
                "La operación no se pudo completar porque viola una restricción de los datos.",
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_body(
                "VALIDATION_ERROR",
                "Los datos enviados no son válidos.",
                jsonable_encoder(exc.errors()),
            ),
        )
