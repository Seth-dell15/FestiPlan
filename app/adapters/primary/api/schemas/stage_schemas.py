from pydantic import BaseModel, Field

from app.domain.models.stage import Stage


class StageCreateRequest(BaseModel):
    festival_id: int
    name: str = Field(min_length=2, max_length=100)
    # Contrôle de format côté HTTP ; la règle métier reste garantie par Stage.
    capacity: int = Field(gt=0)
    available_equipment: list[str] = []


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
