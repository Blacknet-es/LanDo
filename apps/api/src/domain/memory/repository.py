from typing import Protocol

from src.domain.memory.models import MemoryItem


class MemoryRepository(Protocol):
    def save(self, content: str, embedding: list[float]) -> MemoryItem: ...

    def similarity_search(self, embedding: list[float], limit: int = 5) -> list[MemoryItem]: ...
