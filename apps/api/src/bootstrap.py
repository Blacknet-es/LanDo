from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from src.config import settings as app_settings
from src.infrastructure.db import models as _db_models  # noqa: F401
from src.infrastructure.db.readiness import verify_required_extensions
from src.infrastructure.db.session import engine as default_engine
from src.routers import auth, chat, events, health, locations, settings, users, webhooks

API_PREFIX = "/api/v1"


def create_app(database_engine: Engine = default_engine) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        with database_engine.connect() as connection:
            verify_required_extensions(connection)
        yield

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(chat.router, prefix=API_PREFIX)
    app.include_router(events.router, prefix=API_PREFIX)
    app.include_router(locations.router, prefix=API_PREFIX)
    app.include_router(settings.router, prefix=API_PREFIX)
    app.include_router(users.router, prefix=API_PREFIX)
    app.include_router(webhooks.router, prefix=f"{API_PREFIX}/webhooks")

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"message": "Welcome to LanDo API"}

    return app
