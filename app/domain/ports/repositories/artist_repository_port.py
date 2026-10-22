from typing import Protocol

from app.domain.models.artist import Artist


class ArtistRepositoryPort(Protocol):
    def get(self, artist_id: int) -> Artist | None: ...

    def list(self) -> list[Artist]: ...

    def save(self, artist: Artist) -> Artist:
        """Crée l'artiste s'il n'a pas d'id, le met à jour sinon. Renvoie l'artiste avec son id."""
        ...
