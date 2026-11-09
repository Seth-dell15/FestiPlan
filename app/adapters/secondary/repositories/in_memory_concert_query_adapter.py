from app.domain.models.concert import Concert
from app.domain.ports.repositories.concert_query_port import IConcertQueryPort


class InMemoryConcertQueryAdapter(IConcertQueryPort):
    """Adaptateur secondaire en mémoire pour consulter les concerts sans base de données.

    Sert aussi de stockage à InMemoryScheduleRepository, qui y écrit par `add`.
    """

    def __init__(self, initial_concerts: list[Concert] | None = None):
        self._storage: dict[int, Concert] = {}
        self._auto_id: int = 1
        for concert in initial_concerts or []:
            self.add(concert)

    def add(self, concert: Concert) -> Concert:
        """Hors port : alimente le stockage, pour les tests et pour le repository du planning."""
        if concert.id is None:
            concert.id = self._auto_id
        self._auto_id = max(self._auto_id, concert.id + 1)
        self._storage[concert.id] = concert
        return concert

    def get_by_id(self, concert_id: int) -> Concert | None:
        return self._storage.get(concert_id)

    def list_for_festival(self, festival_id: int, include_cancelled: bool = False) -> list[Concert]:
        concerts = [
            c for c in self._storage.values()
            if c.festival_id == festival_id and (include_cancelled or not c.is_cancelled)
        ]
        return sorted(concerts, key=lambda c: c.time_slot.start)

    def list_for_artist(self, artist_id: int) -> list[Concert]:
        concerts = [c for c in self._storage.values() if c.artist_id == artist_id and not c.is_cancelled]
        return sorted(concerts, key=lambda c: c.time_slot.start)
