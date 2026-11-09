from sqlalchemy.orm import Session

from app.domain.models.festival import Festival
from app.domain.ports.repositories.festival_repository_port import (
    FestivalScheduleInfo,
    IFestivalQueryPort,
    IFestivalRepository,
)
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.festival_status import FestivalStatus
from app.adapters.secondary.database.models import Festival as FestivalRow


class FestivalSqlRepository(IFestivalRepository):
    """Traduit entre le modèle ORM legacy et l'entité Festival, sans changer le schéma de la base."""

    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, festival_id: int) -> Festival | None:
        row = self._session.get(FestivalRow, festival_id)
        return _to_entity(row) if row else None

    def list(self) -> list[Festival]:
        rows = self._session.query(FestivalRow).order_by(FestivalRow.id).all()
        return [_to_entity(row) for row in rows]

    def save(self, festival: Festival) -> Festival:
        row = self._session.get(FestivalRow, festival.id) if festival.id else None
        if row is None:
            row = FestivalRow()
            self._session.add(row)
        row.name = festival.name
        row.location = festival.location
        row.start_date = festival.period.start
        row.end_date = festival.period.end
        row.status = festival.status.value
        self._session.commit()
        festival.id = row.id
        return festival


def _to_entity(row: FestivalRow) -> Festival:
    return Festival(
        id=row.id,
        name=row.name,
        location=row.location,
        period=FestivalPeriod(start=row.start_date, end=row.end_date),
        status=FestivalStatus(row.status),
    )


class FestivalSqlQueryAdapter(IFestivalQueryPort):
    """Adaptateur secondaire SQLAlchemy implémentant le port de consultation du festival."""

    def __init__(self, db: Session):
        self._db = db

    def get_schedule_info(self, festival_id: int) -> FestivalScheduleInfo | None:
        orm = self._db.query(FestivalRow).filter(FestivalRow.id == festival_id).first()
        if orm is None:
            return None
        return FestivalScheduleInfo(
            id=orm.id,
            name=orm.name,
            start_date=orm.start_date,
            end_date=orm.end_date,
            is_published=(orm.status == "published"),
        )
