from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models.festival import Festival


class FestivalCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=120)
    start_date: datetime
    end_date: datetime


class FestivalResponse(BaseModel):
    id: int
    name: str
    location: str
    start_date: datetime
    end_date: datetime
    status: str

    @classmethod
    def from_entity(cls, festival: Festival) -> "FestivalResponse":
        return cls(
            id=festival.id,
            name=festival.name,
            location=festival.location,
            start_date=festival.period.start,
            end_date=festival.period.end,
            status=festival.status.value,
        )
