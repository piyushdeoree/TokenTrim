"""Uniform error format: {"error": {"code": str, "message": str, "details": [...]?}}.
Internal details are logged, never returned to the client."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, headers: dict | None = None):
        self.status_code, self.code, self.message, self.headers = status_code, code, message, headers


def not_found(what: str) -> AppError:
    return AppError(404, f"{what.upper().replace(' ', '_')}_NOT_FOUND", f"{what.capitalize()} not found.")


def forbidden(msg: str = "You do not have permission to perform this action.") -> AppError:
    return AppError(403, "FORBIDDEN", msg)


def unauthorized(code: str = "UNAUTHORIZED", msg: str = "Authentication required.") -> AppError:
    return AppError(401, code, msg, {"WWW-Authenticate": "Bearer"})


class NLPServiceError(AppError):
    def __init__(self, msg: str = "The prompt analysis service failed. Please try again later."):
        super().__init__(502, "NLP_SERVICE_ERROR", msg)


class MLServiceError(AppError):
    def __init__(self, msg: str = "The cost estimation service failed. Please try again later."):
        super().__init__(502, "ML_SERVICE_ERROR", msg)


def _body(code: str, message: str, details=None) -> dict:
    err = {"code": code, "message": message}
    if details:
        err["details"] = details
    return {"error": err}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(_body(exc.code, exc.message), status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        # Build details manually: never echo the submitted input back.
        details = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(_body("VALIDATION_ERROR", "Request validation failed.", details), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        return JSONResponse(_body(f"HTTP_{exc.status_code}", str(exc.detail)), status_code=exc.status_code,
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(SQLAlchemyError)
    async def _db(_: Request, exc: SQLAlchemyError):
        logger.exception("Database error")
        return JSONResponse(_body("DATABASE_ERROR", "A database error occurred."), status_code=500)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("Unhandled error")
        return JSONResponse(_body("INTERNAL_ERROR", "An unexpected error occurred."), status_code=500)
