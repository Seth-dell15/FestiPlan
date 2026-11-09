from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.adapters.primary.security.sanitizer import InputSanitizer


class FestivalCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=120)
    start_date: datetime
    end_date: datetime

    @field_validator("name", "location", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v: str) -> str:
        return InputSanitizer.sanitize_text(v) if isinstance(v, str) else v


class FestivalRead(FestivalCreate):
    id: int
    status: str
    model_config = ConfigDict(from_attributes=True)


class ArtistCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    genre: str = Field(min_length=2, max_length=80)
    required_equipment: list[str] = []

    @field_validator("name", "genre", mode="before")
    @classmethod
    def sanitize_text_fields(cls, v: str) -> str:
        return InputSanitizer.sanitize_text(v) if isinstance(v, str) else v


class ArtistRead(BaseModel):
    id: int
    name: str
    genre: str
    required_equipment: list[str]


class StageCreate(BaseModel):
    festival_id: int
    name: str = Field(min_length=2, max_length=100)
    capacity: int = Field(gt=0)
    available_equipment: list[str] = []

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        return InputSanitizer.sanitize_text(v) if isinstance(v, str) else v


class StageRead(BaseModel):
    id: int
    festival_id: int
    name: str
    capacity: int
    available_equipment: list[str]


class ConcertCreate(BaseModel):
    festival_id: int
    artist_id: int
    stage_id: int
    start_time: datetime
    end_time: datetime


class ConcertReschedule(BaseModel):
    start_time: datetime
    end_time: datetime


class ConcertRead(BaseModel):
    id: int
    festival_id: int
    artist_id: int
    stage_id: int
    start_time: datetime
    end_time: datetime
    status: str
    model_config = ConfigDict(from_attributes=True)


class IncidentCreate(BaseModel):
    concert_id: int
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

