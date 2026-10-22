from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.exceptions.logistics_exceptions import FestivalNotFoundError
from app.domain.models.stage import Stage
from app.domain.ports.repositories.festival_repository_port import FestivalRepositoryPort
from app.domain.ports.repositories.stage_repository_port import StageRepositoryPort
from app.domain.value_objects.equipment_set import EquipmentSet


@dataclass(frozen=True)
class CreateStageCommand:
    festival_id: int
    name: str
    capacity: int
    available_equipment: Iterable[str] = ()


class CreateStageUseCase:
    def __init__(self, stage_repository: StageRepositoryPort, festival_repository: FestivalRepositoryPort):
        self._stages = stage_repository
        self._festivals = festival_repository

    def execute(self, command: CreateStageCommand) -> Stage:
        # L'existence du festival demande un repository, donc elle se vérifie ici ; la capacité est vérifiée par Stage.
        if self._festivals.get(command.festival_id) is None:
            raise FestivalNotFoundError(command.festival_id)
        stage = Stage(
            festival_id=command.festival_id,
            name=command.name,
            capacity=command.capacity,
            available_equipment=EquipmentSet.of(command.available_equipment),
        )
        return self._stages.save(stage)
