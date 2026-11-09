"""R8 testée directement sur la politique du domaine, sans repository."""
from datetime import datetime

import pytest

from app.domain.exceptions.operation_exceptions import CannotPublishInvalidScheduleError
from app.domain.models.artist import Artist
from app.domain.models.concert import Concert
from app.domain.models.festival import Festival
from app.domain.models.stage import Stage
from app.domain.services import scheduling_policy as policy
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.time_slot import TimeSlot

FESTIVAL = Festival(
    id=1,
    name="Hellforge",
    location="Clisson",
    period=FestivalPeriod(start=datetime(2027, 6, 18, 10), end=datetime(2027, 6, 20, 23)),
)
STAGES = {1: Stage(id=1, festival_id=1, name="Mainstage", capacity=1000)}
ARTISTS = {1: Artist(id=1, name="Iron Vow", genre="Heavy"), 2: Artist(id=2, name="Abyss", genre="Doom")}


def slot(hour):
    return TimeSlot(datetime(2027, 6, 18, hour), datetime(2027, 6, 18, hour + 1))


def concert(cid=1, artist=1, stage=1, hour=18, festival=1):
    return Concert(id=cid, festival_id=festival, artist_id=artist, stage_id=stage, time_slot=slot(hour))


def test_valid_schedule_is_publishable():
    policy.ensure_publishable(FESTIVAL, [concert(1, artist=1, hour=18), concert(2, artist=2, hour=20)], STAGES, ARTISTS)


def test_empty_schedule_is_not_publishable():
    with pytest.raises(CannotPublishInvalidScheduleError, match="sans concert"):
        policy.ensure_publishable(FESTIVAL, [], STAGES, ARTISTS)


def test_conflict_inside_the_festival_is_not_publishable():
    with pytest.raises(CannotPublishInvalidScheduleError, match="conflit de programmation"):
        policy.ensure_publishable(FESTIVAL, [concert(1, artist=1), concert(2, artist=2)], STAGES, ARTISTS)


def test_artist_booked_in_another_festival_is_not_publishable():
    elsewhere = [concert(9, artist=1, stage=7, festival=2)]

    with pytest.raises(CannotPublishInvalidScheduleError, match="conflit de programmation"):
        policy.ensure_publishable(FESTIVAL, [concert()], STAGES, ARTISTS, elsewhere)


def test_other_artist_booked_elsewhere_does_not_block_publication():
    elsewhere = [concert(9, artist=2, stage=7, festival=2)]

    policy.ensure_publishable(FESTIVAL, [concert()], STAGES, ARTISTS, elsewhere)
