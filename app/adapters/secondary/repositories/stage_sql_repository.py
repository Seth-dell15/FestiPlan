from sqlalchemy.orm import Session

from app.domain.models.stage import Stage
from app.domain.ports.repositories.stage_repository_port import StageRepositoryPort
from app.domain.value_objects.equipment_set import EquipmentSet
from app.models import Stage as StageRow


class StageSqlRepository(StageRepositoryPort):
    """Traduit entre le modèle ORM legacy et l'entité Stage ; les équipements restent stockés en CSV."""

    def __init__(self, session: Session):
        self._session = session

    def get(self, stage_id: int) -> Stage | None:
        row = self._session.get(StageRow, stage_id)
        return _to_entity(row) if row else None

    def list_for_festival(self, festival_id: int) -> list[Stage]:
        rows = self._session.query(StageRow).filter(StageRow.festival_id == festival_id).order_by(StageRow.id).all()
        return [_to_entity(row) for row in rows]

    def save(self, stage: Stage) -> Stage:
        row = self._session.get(StageRow, stage.id) if stage.id else None
        if row is None:
            row = StageRow()
            self._session.add(row)
        row.festival_id = stage.festival_id
        row.name = stage.name
        row.capacity = stage.capacity
        row.available_equipment = stage.available_equipment.to_csv()
        self._session.commit()
        stage.id = row.id
        return stage


def _to_entity(row: StageRow) -> Stage:
    return Stage(
        id=row.id,
        festival_id=row.festival_id,
        name=row.name,
        capacity=row.capacity,
        available_equipment=EquipmentSet.from_csv(row.available_equipment),
    )
