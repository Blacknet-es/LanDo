from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import ForeignKeyConstraint
from sqlmodel import Field, Relationship, SQLModel

from src.domain.locations.models import UserLocation
from src.domain.users.models import User


class LocationTrigger(SQLModel, table=True):
    __tablename__ = "location_triggers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["location_id", "user_id"],
            ["user_locations.id", "user_locations.user_id"],
            name="fk_location_triggers_location_tenant",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    location_id: str = Field(index=True)
    trigger_type: str = Field(max_length=32)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user: User = Relationship()
    location: UserLocation = Relationship(sa_relationship_kwargs={"viewonly": True})
