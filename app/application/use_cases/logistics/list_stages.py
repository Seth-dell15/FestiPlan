from app.domain.models.stage import Stage
from app.domain.ports.repositories.stage_repository_port import StageRepositoryPort


class ListStagesUseCase:
    def __init__(self, stage_repository: StageRepositoryPort):
        self._stages = stage_repository

    def execute(self, festival_id: int) -> list[Stage]:
        return self._stages.list_for_festival(festival_id)
