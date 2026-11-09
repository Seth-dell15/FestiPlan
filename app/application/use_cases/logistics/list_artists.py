from app.domain.models.artist import Artist
from app.domain.ports.repositories.artist_repository_port import IArtistRepository


class ListArtistsUseCase:
    def __init__(self, artist_repository: IArtistRepository):
        self._artists = artist_repository

    def execute(self) -> list[Artist]:
        return self._artists.list()
