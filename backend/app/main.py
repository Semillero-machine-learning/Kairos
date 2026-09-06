"""FastAPI application factory: middlewares, exception handlers and routers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import system
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.modules.auth import router as auth_router

API_V1_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="KAIROS - Plataforma del Semillero de ML",
        version="0.1.0",
        docs_url="/docs" if settings.environment == "development" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(system.router)
    app.include_router(auth_router.router, prefix=API_V1_PREFIX)

    return app


app = create_app()
