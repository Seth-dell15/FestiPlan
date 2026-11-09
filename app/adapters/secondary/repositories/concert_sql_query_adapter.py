from sqlalchemy.orm import Session
from app.adapters.secondary.database.models import Concert as ConcertOrm
from app.domain.models.concert import Concert
from app.domain.value_objects.concert_status import ConcertStatus
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.ports.repositories.concert_query_port import IConcertQueryPort


def to_concert(orm: ConcertOrm) -> Concert:
    """Convertit une ligne SQLAlchemy en entité pure du domaine."""
    return Concert(
        id=orm.id,
        festival_id=orm.festival_id,
        artist_id=orm.artist_id,
        stage_id=orm.stage_id,
        time_slot=TimeSlot(start=orm.start_time, end=orm.end_time),
        status=ConcertStatus(orm.status),
    )


class ConcertSqlQueryAdapter(IConcertQueryPort):
    """Adaptateur secondaire SQLAlchemy pour la consultation des concerts (lecture seule)."""

    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, concert_id: int) -> Concert | None:
        orm = self._db.query(ConcertOrm).filter(ConcertOrm.id == concert_id).first()
        return to_concert(orm) if orm else None

    def list_for_festival(self, festival_id: int, include_cancelled: bool = False) -> list[Concert]:
        query = self._db.query(ConcertOrm).filter(ConcertOrm.festival_id == festival_id)
        if not include_cancelled:
            query = query.filter(ConcertOrm.status != ConcertStatus.CANCELLED.value)

        rows = query.order_by(ConcertOrm.start_time).all()
        return [to_concert(row) for row in rows]

    def list_for_artist(self, artist_id: int) -> list[Concert]:
        rows = (
            self._db.query(ConcertOrm)
            .filter(ConcertOrm.artist_id == artist_id, ConcertOrm.status != ConcertStatus.CANCELLED.value)
            .order_by(ConcertOrm.start_time)
            .all()
        )
        return [to_concert(row) for row in rows]
