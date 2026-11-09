from sqlalchemy.orm import Session

from app.adapters.secondary.database.models import Concert as ConcertOrm
from app.adapters.secondary.database.models import Festival as FestivalOrm
from app.adapters.secondary.repositories.concert_sql_query_adapter import to_concert
from app.domain.models.schedule import Schedule
from app.domain.ports.repositories.schedule_repository_port import IScheduleRepository
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.festival_status import FestivalStatus


class ScheduleSqlRepository(IScheduleRepository):
    """Adaptateur secondaire SQLAlchemy du planning.

    Charge l'agrégat entier (période et état du festival, tous ses concerts) et
    l'enregistre en une seule transaction, sans changer le schéma de la base.
    """

    def __init__(self, db: Session):
        self._db = db

    def get_by_festival_id(self, festival_id: int) -> Schedule | None:
        festival = self._db.get(FestivalOrm, festival_id)
        if festival is None:
            return None
        return Schedule(
            festival_id=festival.id,
            period=FestivalPeriod(start=festival.start_date, end=festival.end_date),
            is_published=festival.status == FestivalStatus.PUBLISHED.value,
            concerts=[to_concert(row) for row in self._concert_rows(festival_id)],
        )

    def get_by_concert_id(self, concert_id: int) -> Schedule | None:
        concert = self._db.get(ConcertOrm, concert_id)
        return self.get_by_festival_id(concert.festival_id) if concert else None

    def save(self, schedule: Schedule) -> None:
        rows = {row.id: row for row in self._concert_rows(schedule.festival_id)}
        saved = []
        for concert in schedule.concerts:
            row = rows.get(concert.id)
            if row is None:
                row = ConcertOrm()
                self._db.add(row)
            row.festival_id = concert.festival_id
            row.artist_id = concert.artist_id
            row.stage_id = concert.stage_id
            row.start_time = concert.time_slot.start
            row.end_time = concert.time_slot.end
            row.status = concert.status.value
            saved.append((concert, row))

        self._db.commit()
        for concert, row in saved:
            concert.id = row.id

    def _concert_rows(self, festival_id: int) -> list[ConcertOrm]:
        return (
            self._db.query(ConcertOrm)
            .filter(ConcertOrm.festival_id == festival_id)
            .order_by(ConcertOrm.start_time)
            .all()
        )
