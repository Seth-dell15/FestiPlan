from typing import Protocol

from app.domain.models.stage import Stage


class StageRepositoryPort(Protocol):
    def get(self, stage_id: int) -> Stage | None: ...

    def list_for_festival(self, festival_id: int) -> list[Stage]: ...

    def save(self, stage: Stage) -> Stage:
        """Crée la scène si elle n'a pas d'id, la met à jour sinon. Renvoie la scène avec son id."""
        ...
