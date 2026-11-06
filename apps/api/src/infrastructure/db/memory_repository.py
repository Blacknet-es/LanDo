from uuid import UUID

from sqlmodel import Session, select

from src.domain.memory.models import MemoryItem
from src.domain.memory.repository import MemoryRepository
from src.infrastructure.db.models import MemoryItemModel


class SqlModelUserMemoryRepository(MemoryRepository):
    def __init__(self, session: Session, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    @staticmethod
    def _to_domain(model: MemoryItemModel) -> MemoryItem:
        return MemoryItem(
            id=model.id,
            user_id=model.user_id,
            content=model.content,
            embedding=tuple(model.embedding),
            created_at=model.created_at,
        )

    def save(self, content: str, embedding: list[float]) -> MemoryItem:
        model = MemoryItemModel(
            user_id=self.user_id,
            content=content,
            embedding=embedding,
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain(model)

    def similarity_search(self, embedding: list[float], limit: int = 5) -> list[MemoryItem]:
        statement = (
            select(MemoryItemModel)
            .where(MemoryItemModel.user_id == self.user_id)
            .order_by(MemoryItemModel.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        return [self._to_domain(model) for model in self.session.exec(statement).all()]
