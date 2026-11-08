from sqlalchemy.orm import Session
from app.models import Artist as ArtistOrm, Stage as StageOrm
from app.domain.ports.repositories.scheduling_catalog_port import (
    ArtistScheduleInfo,
    ISchedulingCatalogPort,
    StageScheduleInfo,
)


def _equipment_from_csv(raw: str | None) -> frozenset[str]:
    """Le schéma hérité stocke les équipements sous forme "a,b,c" : conversion en ensemble."""
    return frozenset(item.strip() for item in (raw or "").split(",") if item.strip())


class SchedulingCatalogSqlAdapter(ISchedulingCatalogPort):
    """Adaptateur secondaire SQLAlchemy : lit scènes et artistes pour le pôle Planification."""

    def __init__(self, db: Session):
        self._db = db

    def get_stage_info(self, stage_id: int) -> StageScheduleInfo | None:
        orm = self._db.query(StageOrm).filter(StageOrm.id == stage_id).first()
        if orm is None:
            return None
        return StageScheduleInfo(
            id=orm.id,
            festival_id=orm.festival_id,
            name=orm.name,
            available_equipment=_equipment_from_csv(orm.available_equipment),
        )

    def get_artist_info(self, artist_id: int) -> ArtistScheduleInfo | None:
        orm = self._db.query(ArtistOrm).filter(ArtistOrm.id == artist_id).first()
        if orm is None:
            return None
        return ArtistScheduleInfo(
            id=orm.id,
            name=orm.name,
            required_equipment=_equipment_from_csv(orm.required_equipment),
        )
