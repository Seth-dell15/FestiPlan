from sqlalchemy.orm import Session
from app.models import Concert as ConcertOrm
from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.ports.repositories.concert_repository_port import IConcertRepository


class ConcertSqlRepository(IConcertRepository):
    """Adaptateur secondaire SQLAlchemy pour la persistance des concerts.
    
    Assure la conversion bidirectionnelle entre le modèle ORM SQLAlchemy (DB)
    et l'entité pure du Domaine (Concert).
    """

    def __init__(self, db: Session):
        self._db = db

    def _to_domain(self, orm: ConcertOrm) -> Concert:
        return Concert(
            id=orm.id,
            festival_id=orm.festival_id,
            artist_id=orm.artist_id,
            stage_id=orm.stage_id,
            time_slot=TimeSlot(start=orm.start_time, end=orm.end_time),
            status=orm.status,
        )

    def _to_orm(self, domain: Concert, existing_orm: ConcertOrm | None = None) -> ConcertOrm:
        orm = existing_orm or ConcertOrm()
        orm.festival_id = domain.festival_id
        orm.artist_id = domain.artist_id
        orm.stage_id = domain.stage_id
        orm.start_time = domain.time_slot.start
        orm.end_time = domain.time_slot.end
        orm.status = domain.status
        return orm

    def get_by_id(self, concert_id: int) -> Concert | None:
        orm = self._db.query(ConcertOrm).filter(ConcertOrm.id == concert_id).first()
        return self._to_domain(orm) if orm else None

    def list_for_festival(self, festival_id: int, include_cancelled: bool = False) -> list[Concert]:
        query = self._db.query(ConcertOrm).filter(ConcertOrm.festival_id == festival_id)
        if not include_cancelled:
            query = query.filter(ConcertOrm.status != "cancelled")
        
        rows = query.order_by(ConcertOrm.start_time).all()
        return [self._to_domain(row) for row in rows]

    def save(self, concert: Concert) -> Concert:
        existing_orm = None
        if concert.id is not None:
            existing_orm = self._db.query(ConcertOrm).filter(ConcertOrm.id == concert.id).first()

        orm = self._to_orm(concert, existing_orm)
        if existing_orm is None:
            self._db.add(orm)

        self._db.commit()
        self._db.refresh(orm)

        concert.id = orm.id
        return concert

    def delete(self, concert_id: int) -> None:
        orm = self._db.query(ConcertOrm).filter(ConcertOrm.id == concert_id).first()
        if orm:
            self._db.delete(orm)
            self._db.commit()
