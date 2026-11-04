"""LanDo API – entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from src.config import settings
from src.infrastructure.db.session import engine
from src.infrastructure.db import models  # Ensures models are registered
from src.domain.settings import models as settings_models  # Ensures user_settings is registered
from src.domain.locations import models as location_models  # Ensures user_locations is registered
from src.routers import health, events, settings as settings_router, chat as chat_router, locations as locations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup if they don't exist
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(
    title="LanDo API",
    description="Self-hosted AI personal assistant backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(events.router)
app.include_router(settings_router.router, prefix="/api")
app.include_router(chat_router.router, prefix="/api")
app.include_router(locations_router.router, prefix="/api")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"message": "LanDo API is running 🧠", "docs": "/docs"}
