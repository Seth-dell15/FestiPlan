from app.domain.models.concert import Concert
from app.domain.ports.repositories.concert_repository_port import IConcertRepository


class InMemoryConcertRepository(IConcertRepository):
    """Adaptateur secondaire en mémoire pour stocker les concerts sans base de données.
    
    Idéal pour les tests unitaires ultra-rapides et le développement isolé.
    """

    def __init__(self, initial_concerts: list[Concert] | None = None):
        self._storage: dict[int, Concert] = {}
        self._auto_id: int = 1
        if initial_concerts:
            for concert in initial_concerts:
                self.save(concert)

    def get_by_id(self, concert_id: int) -> Concert | None:
        return self._storage.get(concert_id)

    def list_for_festival(self, festival_id: int, include_cancelled: bool = False) -> list[Concert]:
        concerts = [
            c for c in self._storage.values()
            if c.festival_id == festival_id and (include_cancelled or not c.is_cancelled)
        ]
        return sorted(concerts, key=lambda c: c.time_slot.start)

    def save(self, concert: Concert) -> Concert:
        if concert.id is None:
            concert.id = self._auto_id
            self._auto_id += 1
        self._storage[concert.id] = concert
        return concert

    def delete(self, concert_id: int) -> None:
        self._storage.pop(concert_id, None)
