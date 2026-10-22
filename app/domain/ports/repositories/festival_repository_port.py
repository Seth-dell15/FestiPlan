from typing import Protocol

from app.domain.models.festival import Festival


class FestivalRepositoryPort(Protocol):
    def get(self, festival_id: int) -> Festival | None: ...

    def list(self) -> list[Festival]: ...

    def save(self, festival: Festival) -> Festival:
        """Crée le festival s'il n'a pas d'id, le met à jour sinon. Renvoie le festival avec son id."""
        ...
