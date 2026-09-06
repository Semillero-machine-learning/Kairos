"""FastAPI application factory: middlewares, exception handlers and routers."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="KAIROS - Plataforma del Semillero de ML",
        version="0.1.0",
    )
    return app


app = create_app()
