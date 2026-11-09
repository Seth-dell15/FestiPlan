from pydantic import BaseModel, Field, field_validator

from app.adapters.primary.security.sanitizer import InputSanitizer
from app.domain.models.artist import Artist


class ArtistCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    genre: str = Field(min_length=2, max_length=80)
    required_equipment: list[str] = []

    @field_validator("name", "genre", mode="before")
    @classmethod
    def sanitize_text_fields(cls, value: str) -> str:
        return InputSanitizer.sanitize_text(value) if isinstance(value, str) else value


class ArtistResponse(BaseModel):
    id: int
    name: str
    genre: str
    required_equipment: list[str]

    @classmethod
    def from_entity(cls, artist: Artist) -> "ArtistResponse":
        return cls(id=artist.id, name=artist.name, genre=artist.genre, required_equipment=list(artist.required_equipment))
