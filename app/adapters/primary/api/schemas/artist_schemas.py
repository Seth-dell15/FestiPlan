from pydantic import BaseModel, Field

from app.domain.models.artist import Artist


class ArtistCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    genre: str = Field(min_length=2, max_length=80)
    required_equipment: list[str] = []


class ArtistResponse(BaseModel):
    id: int
    name: str
    genre: str
    required_equipment: list[str]

    @classmethod
    def from_entity(cls, artist: Artist) -> "ArtistResponse":
        return cls(id=artist.id, name=artist.name, genre=artist.genre, required_equipment=list(artist.required_equipment))
