from app.domain.models.stage import Stage
from app.domain.ports.repositories.stage_repository_port import StageRepositoryPort


class InMemoryStageRepository(StageRepositoryPort):
    """Implémentation en mémoire, pour les tests sans base de données."""

    def __init__(self, initial: list[Stage] | None = None):
        self._storage: dict[int, Stage] = {}
        self._next_id = 1
        for stage in initial or []:
            self.save(stage)

    def get(self, stage_id: int) -> Stage | None:
        return self._storage.get(stage_id)

    def list_for_festival(self, festival_id: int) -> list[Stage]:
        stages = [stage for stage in self._storage.values() if stage.belongs_to(festival_id)]
        return sorted(stages, key=lambda stage: stage.id)

    def save(self, stage: Stage) -> Stage:
        if stage.id is None:
            stage.id = self._next_id
            self._next_id += 1
        self._storage[stage.id] = stage
        return stage
