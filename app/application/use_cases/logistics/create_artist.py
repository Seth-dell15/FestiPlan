from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.models.artist import Artist
from app.domain.ports.repositories.artist_repository_port import ArtistRepositoryPort
from app.domain.value_objects.equipment_set import EquipmentSet


@dataclass(frozen=True)
class CreateArtistCommand:
    name: str
    genre: str
    required_equipment: Iterable[str] = ()


class CreateArtistUseCase:
    def __init__(self, artist_repository: ArtistRepositoryPort):
        self._artists = artist_repository

    def execute(self, command: CreateArtistCommand) -> Artist:
        artist = Artist(
            name=command.name,
            genre=command.genre,
            required_equipment=EquipmentSet.of(command.required_equipment),
        )
        return self._artists.save(artist)
