from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  enregistre les tables dans Base.metadata
from app.adapters.secondary.repositories.artist_sql_repository import ArtistSqlRepository
from app.adapters.secondary.repositories.festival_sql_repository import FestivalSqlRepository
from app.adapters.secondary.repositories.stage_sql_repository import StageSqlRepository
from app.database import Base
from app.domain.models.artist import Artist
from app.domain.models.festival import Festival
from app.domain.models.stage import Stage
from app.domain.value_objects.equipment_set import EquipmentSet
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.festival_status import FestivalStatus
from app.models import Artist as ArtistRow


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()
    engine.dispose()


def make_festival():
    return Festival(
        name="Hellforge Open Air",
        location="Clisson-sur-Rivière",
        period=FestivalPeriod(start=datetime(2027, 6, 18, 10, 0), end=datetime(2027, 6, 20, 23, 59)),
    )


def test_festival_round_trip_keeps_period_and_status(session):
    repository = FestivalSqlRepository(session)
    saved = repository.save(make_festival())

    loaded = repository.get(saved.id)

    assert loaded.name == "Hellforge Open Air"
    assert loaded.period == saved.period
    assert loaded.status is FestivalStatus.PREPARATION


def test_festival_save_updates_existing_row(session):
    repository = FestivalSqlRepository(session)
    festival = repository.save(make_festival())
    festival.status = FestivalStatus.PUBLISHED

    repository.save(festival)

    assert [f.status for f in repository.list()] == [FestivalStatus.PUBLISHED]


def test_unknown_festival_is_none(session):
    assert FestivalSqlRepository(session).get(42) is None


def test_artist_equipment_is_stored_as_csv_and_read_back_as_set(session):
    repository = ArtistSqlRepository(session)
    artist = repository.save(
        Artist(name="Iron Vow", genre="Heavy metal", required_equipment=EquipmentSet.of(["pyro", "double_kick"]))
    )

    assert session.get(ArtistRow, artist.id).required_equipment == "double_kick,pyro"
    assert repository.get(artist.id).required_equipment == EquipmentSet.of(["pyro", "double_kick"])


def test_stages_are_listed_per_festival(session):
    festival_id = FestivalSqlRepository(session).save(make_festival()).id
    other_id = FestivalSqlRepository(session).save(make_festival()).id
    repository = StageSqlRepository(session)
    valley = repository.save(Stage(festival_id=festival_id, name="Valley", capacity=8000))
    repository.save(Stage(festival_id=other_id, name="Altar", capacity=5000))

    stages = repository.list_for_festival(festival_id)

    assert [stage.id for stage in stages] == [valley.id]
    assert stages[0].available_equipment == EquipmentSet()
