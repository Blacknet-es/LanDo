"""
Database session management and engine configuration.
"""

from typing import Generator
from sqlmodel import Session, create_engine
from src.config import settings

# In production or standard dev, use PostgreSQL from settings
# For tests, engine can be overridden or SQLite can be used.
engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)


def get_session() -> Generator[Session, None, None]:
    """Dependency that yields a database session."""
    with Session(engine) as session:
        yield session

