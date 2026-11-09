"""R8 testée directement sur le planning, sans repository."""
from datetime import datetime

import pytest

from app.domain.exceptions.operation_exceptions import CannotPublishInvalidScheduleError
from app.domain.models.artist import Artist
from app.domain.models.concert import Concert
from app.domain.models.schedule import Schedule
from app.domain.models.stage import Stage
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.time_slot import TimeSlot

PERIOD = FestivalPeriod(start=datetime(2027, 6, 18, 10), end=datetime(2027, 6, 20, 23))
STAGES = {1: Stage(id=1, festival_id=1, name="Mainstage", capacity=1000)}
ARTISTS = {1: Artist(id=1, name="Iron Vow", genre="Heavy"), 2: Artist(id=2, name="Abyss", genre="Doom")}


def slot(hour):
    return TimeSlot(datetime(2027, 6, 18, hour), datetime(2027, 6, 18, hour + 1))


def concert(cid=1, artist=1, stage=1, hour=18, festival=1):
    return Concert(id=cid, festival_id=festival, artist_id=artist, stage_id=stage, time_slot=slot(hour))


def schedule(*concerts):
    return Schedule(festival_id=1, period=PERIOD, concerts=list(concerts))


def test_valid_schedule_is_publishable():
    schedule(concert(1, artist=1, hour=18), concert(2, artist=2, hour=20)).ensure_publishable(STAGES, ARTISTS)


def test_empty_schedule_is_not_publishable():
    with pytest.raises(CannotPublishInvalidScheduleError, match="sans concert"):
        schedule().ensure_publishable(STAGES, ARTISTS)


def test_schedule_with_only_cancelled_concerts_is_not_publishable():
    cancelled = concert()
    cancelled.cancel()

    with pytest.raises(CannotPublishInvalidScheduleError, match="sans concert"):
        schedule(cancelled).ensure_publishable(STAGES, ARTISTS)


def test_conflict_inside_the_festival_is_not_publishable():
    with pytest.raises(CannotPublishInvalidScheduleError, match="conflit de programmation"):
        schedule(concert(1, artist=1), concert(2, artist=2)).ensure_publishable(STAGES, ARTISTS)


def test_concert_outside_the_festival_is_not_publishable():
    late = Concert(
        id=1, festival_id=1, artist_id=1, stage_id=1,
        time_slot=TimeSlot(datetime(2027, 6, 21, 18), datetime(2027, 6, 21, 19)),
    )

    with pytest.raises(CannotPublishInvalidScheduleError, match="R6"):
        schedule(late).ensure_publishable(STAGES, ARTISTS)


def test_artist_booked_in_another_festival_is_not_publishable():
    elsewhere = [concert(9, artist=1, stage=7, festival=2)]

    with pytest.raises(CannotPublishInvalidScheduleError, match="conflit de programmation"):
        schedule(concert()).ensure_publishable(STAGES, ARTISTS, elsewhere)


def test_other_artist_booked_elsewhere_does_not_block_publication():
    elsewhere = [concert(9, artist=2, stage=7, festival=2)]

    schedule(concert()).ensure_publishable(STAGES, ARTISTS, elsewhere)
