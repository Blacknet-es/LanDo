from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlmodel import SQLModel

from src.domain.locations.triggers import LocationTrigger  # noqa: F401
from src.domain.memory.models import MemoryItem  # noqa: F401
from src.infrastructure.db.session import engine
from src.routers import auth, chat, events, health, locations, settings, webhooks


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with engine.begin() as connection:
        vector_version = connection.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one_or_none()
        if vector_version is None:
            raise RuntimeError(
                "PostgreSQL pgvector is not enabled. Initialize the database with "
                "apps/db/init/01-pgvector.sql."
            )
        SQLModel.metadata.create_all(connection)
    yield


app = FastAPI(lifespan=lifespan)
API_PREFIX = "/api/v1"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.include_router(webhooks.router, prefix=f"{API_PREFIX}/webhooks")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"message": "Welcome to LanDo API"}
