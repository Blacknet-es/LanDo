from uuid import UUID

from sqlmodel import Session, select

from src.domain.memory.models import MemoryItem


class UserMemoryRepository:
    def __init__(self, session: Session, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    def save(self, content: str, embedding: list[float]) -> MemoryItem:
        item = MemoryItem(
            user_id=self.user_id,
            content=content,
            embedding=embedding,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def similarity_search(self, embedding: list[float], limit: int = 5) -> list[MemoryItem]:
        statement = (
            select(MemoryItem)
            .where(MemoryItem.user_id == self.user_id)
            .order_by(MemoryItem.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        return list(self.session.exec(statement).all())
