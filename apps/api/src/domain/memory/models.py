from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class MemoryItem:
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    content: str = ""
    embedding: tuple[float, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
