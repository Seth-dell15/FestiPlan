from sqlalchemy.orm import Session
from app.models import Festival as FestivalOrm
from app.domain.ports.repositories.festival_repository_port import (
    IFestivalQueryPort,
    FestivalScheduleInfo,
)


class FestivalSqlQueryAdapter(IFestivalQueryPort):
    """Adaptateur secondaire SQLAlchemy implémentant le port de consultation du festival."""

    def __init__(self, db: Session):
        self._db = db

    def get_schedule_info(self, festival_id: int) -> FestivalScheduleInfo | None:
        orm = self._db.query(FestivalOrm).filter(FestivalOrm.id == festival_id).first()
        if orm is None:
            return None
        return FestivalScheduleInfo(
            id=orm.id,
            name=orm.name,
            start_date=orm.start_date,
            end_date=orm.end_date,
            is_published=(orm.status == "published"),
        )
