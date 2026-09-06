"""FastAPI application factory: middlewares, exception handlers and routers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers


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

    return app


app = create_app()
