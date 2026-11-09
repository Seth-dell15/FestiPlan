from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.secondary.database import models  # noqa: F401  enregistre les tables dans Base.metadata
from app.adapters.secondary.repositories.artist_sql_repository import ArtistSqlRepository
from app.adapters.secondary.repositories.concert_sql_query_adapter import ConcertSqlQueryAdapter
from app.adapters.secondary.repositories.festival_sql_repository import FestivalSqlRepository
from app.adapters.secondary.repositories.incident_sql_repository import IncidentSqlRepository
from app.adapters.secondary.repositories.schedule_sql_repository import ScheduleSqlRepository
from app.adapters.secondary.repositories.stage_sql_repository import StageSqlRepository
from app.adapters.secondary.database.session import Base
from app.domain.models.artist import Artist
from app.domain.models.concert import Concert
from app.domain.models.festival import Festival
from app.domain.models.incident import Incident
from app.domain.models.stage import Stage
from app.domain.value_objects.concert_status import ConcertStatus
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.time_slot import TimeSlot
from app.adapters.secondary.database.models import Concert as ConcertRow


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


def save_concert(session, concert):
    """Enregistre un concert par le planning de son festival, sans appliquer les règles (données de test)."""
    repository = ScheduleSqlRepository(session)
    schedule = repository.get_by_festival_id(concert.festival_id)
    schedule.concerts.append(concert)
    repository.save(schedule)
    return concert


def test_schedule_round_trip_keeps_period_publication_and_concerts(session, references):
    repository = ScheduleSqlRepository(session)
    festival_id = references[0]

    saved = save_concert(session, make_concert(references))
    schedule = repository.get_by_festival_id(festival_id)
    loaded = schedule.get_concert(saved.id)

    assert saved.id is not None
    assert schedule.period == FestivalPeriod(start=datetime(2027, 6, 18, 10), end=datetime(2027, 6, 20, 23))
    assert schedule.is_published is False
    assert loaded.time_slot == TimeSlot(datetime(2027, 6, 18, 18), datetime(2027, 6, 18, 19))
    assert loaded.status is ConcertStatus.SCHEDULED


def test_schedule_save_updates_existing_row(session, references):
    repository = ScheduleSqlRepository(session)
    concert = save_concert(session, make_concert(references))

    schedule = repository.get_by_concert_id(concert.id)
    schedule.cancel_concert(concert.id)
    repository.save(schedule)

    assert session.query(ConcertRow).count() == 1
    assert session.get(ConcertRow, concert.id).status == "cancelled"
    assert ConcertSqlQueryAdapter(session).get_by_id(concert.id).is_cancelled


def test_schedule_reflects_the_publication_of_its_festival(session, references):
    festivals = FestivalSqlRepository(session)
    festival = festivals.get_by_id(references[0])
    festival.publish()
    festivals.save(festival)

    assert ScheduleSqlRepository(session).get_by_festival_id(festival.id).is_published is True


def test_schedule_is_found_from_one_of_its_concerts(session, references):
    concert = save_concert(session, make_concert(references))
    repository = ScheduleSqlRepository(session)

    assert repository.get_by_concert_id(concert.id).festival_id == references[0]
    assert repository.get_by_concert_id(42) is None
    assert repository.get_by_festival_id(42) is None


def test_concerts_are_listed_chronologically_without_cancelled_by_default(session, references):
    repository = ConcertSqlQueryAdapter(session)
    late = save_concert(session, make_concert(references, hour=20))
    early = save_concert(session, make_concert(references, hour=14))
    cancelled = make_concert(references, hour=16)
    cancelled.cancel()
    cancelled = save_concert(session, cancelled)
    festival_id = references[0]

    assert [c.id for c in repository.list_for_festival(festival_id)] == [early.id, late.id]
    assert [c.id for c in repository.list_for_festival(festival_id, include_cancelled=True)] == [
        early.id,
        cancelled.id,
        late.id,
    ]


def test_concerts_of_an_artist_are_listed_across_festivals_without_cancelled(session, references):
    festival_id, artist_id, stage_id = references
    other_festival = FestivalSqlRepository(session).save(
        Festival(
            name="Autre",
            location="Nantes",
            period=FestivalPeriod(start=datetime(2027, 6, 18, 10), end=datetime(2027, 6, 20, 23)),
        )
    )
    other_artist = ArtistSqlRepository(session).save(Artist(name="Abyss", genre="Doom"))
    repository = ConcertSqlQueryAdapter(session)
    late = save_concert(session, make_concert(references, hour=20))
    elsewhere = make_concert(references, hour=14)
    elsewhere.festival_id = other_festival.id
    elsewhere = save_concert(session, elsewhere)
    cancelled = make_concert(references, hour=16)
    cancelled.cancel()
    save_concert(session, cancelled)
    save_concert(session, make_concert((festival_id, other_artist.id, stage_id), hour=18))

    assert [c.id for c in repository.list_for_artist(artist_id)] == [elsewhere.id, late.id]


def test_unknown_concert_is_none(session):
    assert ConcertSqlQueryAdapter(session).get_by_id(42) is None


def test_incident_round_trip_and_resolution(session, references):
    concert = save_concert(session, make_concert(references))
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
    first_concert = save_concert(session, make_concert(references, hour=14))
    second_concert = save_concert(session, make_concert(references, hour=16))
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
