from uuid import uuid4

from sqlalchemy.dialects import postgresql

from src.domain.memory.repository import UserMemoryRepository


class _Result:
    def all(self):
        return []


class _Session:
    def add(self, item):
        self.item = item

    def commit(self):
        pass

    def refresh(self, _item):
        pass

    def exec(self, statement):
        self.statement = statement
        return _Result()


def test_memory_save_assigns_repository_owner():
    user_id = uuid4()
    session = _Session()
    repository = UserMemoryRepository(session, user_id)

    item = repository.save("private memory", [0.1, 0.2])

    assert item.user_id == user_id
    assert item.content == "private memory"
    assert item.embedding == [0.1, 0.2]


def test_memory_search_query_always_filters_by_owner():
    user_id = uuid4()
    session = _Session()
    repository = UserMemoryRepository(session, user_id)

    assert repository.similarity_search([0.1, 0.2]) == []

    compiled = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "memory_items.user_id" in compiled
    assert user_id in session.statement.compile(dialect=postgresql.dialect()).params.values()
