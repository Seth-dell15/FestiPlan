from pydantic import BaseModel, Field, field_validator

from app.adapters.primary.api.schemas.common import MAX_STORED_INT, EntityId
from app.adapters.primary.security.sanitizer import InputSanitizer
from app.domain.models.stage import Stage


class StageCreateRequest(BaseModel):
    festival_id: EntityId
    name: str = Field(min_length=2, max_length=100)
    # Contrôle de format côté HTTP ; la règle métier reste garantie par Stage.
    capacity: int = Field(gt=0, le=MAX_STORED_INT)
    available_equipment: list[str] = []

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, value: str) -> str:
        return InputSanitizer.sanitize_text(value) if isinstance(value, str) else value


class StageResponse(BaseModel):
    id: int
    festival_id: int
    name: str
    capacity: int
    available_equipment: list[str]

    @classmethod
    def from_entity(cls, stage: Stage) -> "StageResponse":
        return cls(
            id=stage.id,
            festival_id=stage.festival_id,
            name=stage.name,
            capacity=stage.capacity,
            available_equipment=list(stage.available_equipment),
        )
