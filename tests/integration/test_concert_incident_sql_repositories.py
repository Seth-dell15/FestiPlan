from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  enregistre les tables dans Base.metadata
from app.adapters.secondary.repositories.artist_sql_repository import ArtistSqlRepository
from app.adapters.secondary.repositories.concert_sql_repository import ConcertSqlRepository
from app.adapters.secondary.repositories.festival_sql_repository import FestivalSqlRepository
from app.adapters.secondary.repositories.incident_sql_repository import IncidentSqlRepository
from app.adapters.secondary.repositories.stage_sql_repository import StageSqlRepository
from app.database import Base
from app.domain.models.artist import Artist
from app.domain.models.concert import Concert
from app.domain.models.festival import Festival
from app.domain.models.incident import Incident
from app.domain.models.stage import Stage
from app.domain.value_objects.concert_status import ConcertStatus
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.time_slot import TimeSlot
from app.models import Concert as ConcertRow


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()
    engine.dispose()


@pytest.fixture
def references(session):
    festival = FestivalSqlRepository(session).save(
        Festival(
            name="Hellforge",
            location="Clisson",
            period=FestivalPeriod(start=datetime(2027, 6, 18, 10), end=datetime(2027, 6, 20, 23)),
        )
    )
    artist = ArtistSqlRepository(session).save(Artist(name="Iron Vow", genre="Heavy"))
    stage = StageSqlRepository(session).save(Stage(festival_id=festival.id, name="Mainstage", capacity=1000))
    return festival.id, artist.id, stage.id


def make_concert(references, hour=18):
    festival_id, artist_id, stage_id = references
    return Concert(
        festival_id=festival_id,
        artist_id=artist_id,
        stage_id=stage_id,
        time_slot=TimeSlot(datetime(2027, 6, 18, hour), datetime(2027, 6, 18, hour + 1)),
    )


def test_concert_round_trip_keeps_time_slot_and_status(session, references):
    repository = ConcertSqlRepository(session)

    saved = repository.save(make_concert(references))
    loaded = repository.get_by_id(saved.id)

    assert saved.id is not None
    assert loaded.time_slot == TimeSlot(datetime(2027, 6, 18, 18), datetime(2027, 6, 18, 19))
    assert loaded.status is ConcertStatus.SCHEDULED


def test_concert_save_updates_existing_row(session, references):
    repository = ConcertSqlRepository(session)
    concert = repository.save(make_concert(references))

    concert.cancel()
    repository.save(concert)

    assert session.query(ConcertRow).count() == 1
    assert session.get(ConcertRow, concert.id).status == "cancelled"
    assert repository.get_by_id(concert.id).is_cancelled


def test_concerts_are_listed_chronologically_without_cancelled_by_default(session, references):
    repository = ConcertSqlRepository(session)
    late = repository.save(make_concert(references, hour=20))
    early = repository.save(make_concert(references, hour=14))
    cancelled = make_concert(references, hour=16)
    cancelled.cancel()
    cancelled = repository.save(cancelled)
    festival_id = references[0]

    assert [c.id for c in repository.list_for_festival(festival_id)] == [early.id, late.id]
    assert [c.id for c in repository.list_for_festival(festival_id, include_cancelled=True)] == [
        early.id,
        cancelled.id,
        late.id,
    ]


def test_unknown_concert_is_none(session):
    assert ConcertSqlRepository(session).get_by_id(42) is None


def test_incident_round_trip_and_resolution(session, references):
    concert = ConcertSqlRepository(session).save(make_concert(references))
    repository = IncidentSqlRepository(session)
    occurred_at = datetime(2027, 6, 18, 18, 30)

    incident = repository.save(Incident(concert_id=concert.id, description="Panne son", occurred_at=occurred_at))
    incident.resolve()
    repository.save(incident)
    loaded = repository.get_by_id(incident.id)

    assert (loaded.concert_id, loaded.description, loaded.occurred_at) == (concert.id, "Panne son", occurred_at)
    assert loaded.resolved is True
    assert len(repository.list_all()) == 1


def test_incidents_are_listed_most_recent_first_and_filtered_by_concert(session, references):
    concerts = ConcertSqlRepository(session)
    first_concert = concerts.save(make_concert(references, hour=14))
    second_concert = concerts.save(make_concert(references, hour=16))
    repository = IncidentSqlRepository(session)
    older = repository.save(
        Incident(concert_id=first_concert.id, description="Ancien", occurred_at=datetime(2027, 6, 18, 14, 10))
    )
    newer = repository.save(
        Incident(concert_id=first_concert.id, description="Récent", occurred_at=datetime(2027, 6, 18, 14, 40))
    )
    other = repository.save(
        Incident(concert_id=second_concert.id, description="Autre", occurred_at=datetime(2027, 6, 18, 16, 10))
    )

    assert [i.id for i in repository.list_by_concert(first_concert.id)] == [newer.id, older.id]
    assert [i.id for i in repository.list_all()] == [other.id, newer.id, older.id]


def test_unknown_incident_is_none(session):
    assert IncidentSqlRepository(session).get_by_id(42) is None
