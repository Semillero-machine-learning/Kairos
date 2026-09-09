"""FastAPI application factory: middlewares, exception handlers and routers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import system
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.modules.auth import invitations_router
from app.modules.auth import router as auth_router
from app.modules.lessons import lessons_router, resources_router
from app.modules.lessons import router as lesson_modules_router
from app.modules.notifications import admin_router as notification_settings_router
from app.modules.notifications import router as notifications_router
from app.modules.projects import members_router, permissions_router, roles_router
from app.modules.projects import router as projects_router
from app.modules.tasks import comments_router, me_router, submissions_router, tasks_router
from app.modules.tasks import router as project_tasks_router
from app.modules.users import router as users_router

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
    app.include_router(invitations_router.router, prefix=API_V1_PREFIX)
    app.include_router(users_router.router, prefix=API_V1_PREFIX)
    app.include_router(projects_router.router, prefix=API_V1_PREFIX)
    app.include_router(members_router.router, prefix=API_V1_PREFIX)
    app.include_router(roles_router.router, prefix=API_V1_PREFIX)
    app.include_router(permissions_router.router, prefix=API_V1_PREFIX)
    app.include_router(project_tasks_router.router, prefix=API_V1_PREFIX)
    app.include_router(tasks_router.router, prefix=API_V1_PREFIX)
    app.include_router(me_router.router, prefix=API_V1_PREFIX)
    app.include_router(submissions_router.router, prefix=API_V1_PREFIX)
    app.include_router(comments_router.router, prefix=API_V1_PREFIX)
    app.include_router(notifications_router.router, prefix=API_V1_PREFIX)
    app.include_router(notification_settings_router.router, prefix=API_V1_PREFIX)
    app.include_router(lesson_modules_router.router, prefix=API_V1_PREFIX)
    app.include_router(lessons_router.router, prefix=API_V1_PREFIX)
    app.include_router(resources_router.router, prefix=API_V1_PREFIX)

    return app


app = create_app()
