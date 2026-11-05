"""
Unit tests for Locations domain and use cases.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.application.locations.use_cases import (
    CreateUserLocationDTO,
    CreateUserLocationUseCase,
    ListUserLocationsUseCase,
)
from src.domain.locations.exceptions import InvalidCoordinatesException
from src.domain.locations.models import UserLocation
from src.domain.locations.repository import SqlModelLocationRepository
from src.domain.users.models import User
from tests.auth_utils import get_test_user_id


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(email="locations@example.com", hashed_password="unused")
        session.add(user)
        session.commit()
        session.info["test_user_id"] = user.id
        yield session
    SQLModel.metadata.drop_all(engine)


class TestLocationsDomain:
    def test_create_valid_location(self, session: Session):
        user_id = get_test_user_id(session)
        repo = SqlModelLocationRepository(session, user_id)
        use_case = CreateUserLocationUseCase(repo, user_id)

        dto = CreateUserLocationDTO(
            name="Casa de mis padres",
            latitude=40.4168,
            longitude=-3.7038,
            radius_meters=150,
        )
        location = use_case.execute(dto)

        assert location.id is not None
        assert location.name == "Casa de mis padres"
        assert location.latitude == 40.4168
        assert location.longitude == -3.7038
        assert location.radius_meters == 150

    def test_invalid_coordinates_raise_exception(self, session: Session):
        user_id = get_test_user_id(session)
        repo = SqlModelLocationRepository(session, user_id)
        use_case = CreateUserLocationUseCase(repo, user_id)

        dto = CreateUserLocationDTO(
            name="Invalid Place",
            latitude=95.0,  # Invalid latitude > 90
            longitude=0.0,
            radius_meters=100,
        )
        with pytest.raises(InvalidCoordinatesException):
            use_case.execute(dto)

    def test_list_locations_case_insensitive_lookup(self, session: Session):
        user_id = get_test_user_id(session)
        repo = SqlModelLocationRepository(session, user_id)
        loc1 = UserLocation(user_id=user_id, name="Office", latitude=40.0, longitude=-3.0)
        loc2 = UserLocation(user_id=user_id, name="Gym", latitude=40.1, longitude=-3.1)
        repo.save(loc1)
        repo.save(loc2)

        list_uc = ListUserLocationsUseCase(repo)
        all_locs = list_uc.execute()
        assert len(all_locs) == 2

        # Test find_by_name case-insensitivity
        found = repo.find_by_name("office")
        assert found is not None
        assert found.name == "Office"

        not_found = repo.find_by_name("Nonexistent")
        assert not_found is None
