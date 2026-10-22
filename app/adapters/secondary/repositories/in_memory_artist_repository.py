from app.domain.models.artist import Artist
from app.domain.ports.repositories.artist_repository_port import ArtistRepositoryPort


class InMemoryArtistRepository(ArtistRepositoryPort):
    """Implémentation en mémoire, pour les tests sans base de données."""

    def __init__(self, initial: list[Artist] | None = None):
        self._storage: dict[int, Artist] = {}
        self._next_id = 1
        for artist in initial or []:
            self.save(artist)

    def get(self, artist_id: int) -> Artist | None:
        return self._storage.get(artist_id)

    def list(self) -> list[Artist]:
        return sorted(self._storage.values(), key=lambda artist: artist.name)

    def save(self, artist: Artist) -> Artist:
        if artist.id is None:
            artist.id = self._next_id
            self._next_id += 1
        self._storage[artist.id] = artist
        return artist
