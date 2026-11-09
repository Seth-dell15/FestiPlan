from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.adapters.primary.api.schemas.common import EntityId
from app.adapters.primary.security.sanitizer import InputSanitizer


class IncidentCreate(BaseModel):
    concert_id: EntityId
    description: str = Field(min_length=3, max_length=2000)
    occurred_at: datetime | None = None

    @field_validator("description", mode="before")
    @classmethod
    def sanitize_description(cls, v: str) -> str:
        return InputSanitizer.sanitize_text(v) if isinstance(v, str) else v


class IncidentRead(BaseModel):
    id: int
    concert_id: int
    description: str
    occurred_at: datetime
    resolved: bool
    model_config = ConfigDict(from_attributes=True)
