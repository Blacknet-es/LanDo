from datetime import datetime, timezone
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Text
from sqlalchemy.ext.compiler import compiles
from sqlmodel import Field, Relationship, SQLModel

from src.domain.users.models import User


@compiles(Vector, "sqlite")
def _compile_vector_for_sqlite(_type: Vector, _compiler: object, **_kwargs: object) -> str:
    return "TEXT"


class MemoryItem(SQLModel, table=True):
    __tablename__ = "memory_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    content: str = Field(sa_column=Column(Text, nullable=False))
    embedding: list[float] = Field(sa_column=Column(Vector(), nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user: User = Relationship()
