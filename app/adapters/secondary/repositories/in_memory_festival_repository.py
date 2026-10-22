from app.domain.models.festival import Festival
from app.domain.ports.repositories.festival_repository_port import FestivalRepositoryPort


class InMemoryFestivalRepository(FestivalRepositoryPort):
    """Implémentation en mémoire, pour les tests sans base de données."""

    def __init__(self, initial: list[Festival] | None = None):
        self._storage: dict[int, Festival] = {}
        self._next_id = 1
        for festival in initial or []:
            self.save(festival)

    def get(self, festival_id: int) -> Festival | None:
        return self._storage.get(festival_id)

    def list(self) -> list[Festival]:
        return sorted(self._storage.values(), key=lambda festival: festival.id)

    def save(self, festival: Festival) -> Festival:
        if festival.id is None:
            festival.id = self._next_id
            self._next_id += 1
        self._storage[festival.id] = festival
        return festival
