import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api import api_keys, auth, dashboard, models, projects, prompts, teams, usage
from app.core.config import settings
from app.core.exceptions import AppError
from app.database.seed import seed_models
from app.database.session import SessionLocal

log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.SEED_ON_STARTUP:
        db = SessionLocal()
        try:
            seed_models(db)  # requires migrations to have been applied
        except Exception:
            log.exception("Seeding skipped (have you run `alembic upgrade head`?)")
        finally:
            db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend for the AI Cost Intelligence and Prompt Optimization Platform. "
                "Authenticate with a JWT (`/auth/login`) or an `X-API-Key` header.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])


def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


@app.exception_handler(AppError)
async def app_error_handler(_req: Request, exc: AppError):
    return _error(exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_handler(_req: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return _error(422, "VALIDATION_ERROR", "Invalid request.", details)


@app.exception_handler(SQLAlchemyError)
async def db_handler(_req: Request, exc: SQLAlchemyError):
    log.exception("Database error", exc_info=exc)
    return _error(500, "DATABASE_ERROR", "A database error occurred.")


@app.exception_handler(Exception)
async def unhandled_handler(_req: Request, exc: Exception):
    log.exception("Unhandled error", exc_info=exc)  # stack trace goes to logs only, never to the client
    return _error(500, "INTERNAL_ERROR", "An unexpected error occurred.")


for r in (auth.router, projects.router, prompts.router, usage.router, dashboard.router,
          api_keys.router, teams.router, models.router):
    app.include_router(r)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
