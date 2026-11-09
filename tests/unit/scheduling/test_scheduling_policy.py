"""Tests unitaires du domaine Planification : sans FastAPI ni base de données."""
from datetime import datetime, timedelta, timezone
import pytest

from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.services import scheduling_policy as policy
from app.domain.ports.repositories.festival_repository_port import FestivalScheduleInfo
from app.domain.exceptions.logistics_exceptions import EquipmentMismatchError
from app.domain.models.artist import Artist
from app.domain.models.stage import Stage
from app.domain.value_objects.equipment_set import EquipmentSet
from app.domain.exceptions.scheduling_exceptions import (
    ArtistAlreadyBookedError,
    CannotModifyPublishedFestivalError,
    ConcertAlreadyCancelledError,
    ConcertOutsideFestivalError,
    InvalidTimeSlotError,
    StageNotInFestivalError,
    StageOccupiedError,
)

FESTIVAL = FestivalScheduleInfo(
    id=1, name="Hellforge", start_date=datetime(2027, 6, 18, 10), end_date=datetime(2027, 6, 20, 23, 59),
    is_published=False,
)


def slot(h1, h2, day=18):
    return TimeSlot(datetime(2027, 6, day, h1), datetime(2027, 6, day, h2))


def concert(cid, artist, stage, s, status="scheduled"):
    return Concert(id=cid, festival_id=1, artist_id=artist, stage_id=stage, time_slot=s, status=status)


# --- TimeSlot -------------------------------------------------------------------

def test_time_slot_duration():
    assert slot(18, 20).duration == timedelta(hours=2)


def test_back_to_back_slots_do_not_overlap():
    assert not slot(18, 19).overlaps(slot(19, 20))
    assert not slot(19, 20).overlaps(slot(18, 19))


def test_contained_slot_overlaps():
    assert slot(18, 22).overlaps(slot(19, 20))
    assert slot(19, 20).overlaps(slot(18, 22))


def test_timezone_aware_dates_are_normalized_to_naive_utc():
    paris = timezone(timedelta(hours=2))
    s = TimeSlot(datetime(2027, 6, 18, 20, tzinfo=paris), datetime(2027, 6, 18, 21, tzinfo=paris))
    assert s.start == datetime(2027, 6, 18, 18) and s.start.tzinfo is None
    # comparable aux dates naïves stockées en base, sans TypeError
    assert s.overlaps(slot(18, 19))
    assert s.is_within(FESTIVAL.start_date, FESTIVAL.end_date)


def test_mixed_naive_and_aware_bounds_are_validated():
    with pytest.raises(InvalidTimeSlotError):
        TimeSlot(datetime(2027, 6, 18, 20), datetime(2027, 6, 18, 19, tzinfo=timezone.utc))


# --- Concert --------------------------------------------------------------------

def test_cancelled_concert_cannot_be_rescheduled():
    c = concert(1, 10, 100, slot(18, 19), status="cancelled")
    with pytest.raises(ConcertAlreadyCancelledError):
        c.reschedule(slot(20, 21))


def test_concert_cannot_be_cancelled_twice():
    c = concert(1, 10, 100, slot(18, 19))
    c.cancel()
    with pytest.raises(ConcertAlreadyCancelledError):
        c.cancel()


def test_reschedule_emits_event_with_previous_and_new_slot():
    c = concert(1, 10, 100, slot(18, 19))
    event = c.reschedule(slot(20, 21))
    assert event.concert_id == 1
    assert event.previous_time_slot == slot(18, 19)
    assert event.new_time_slot == slot(20, 21)


# --- Politique de programmation -------------------------------------------------

def test_r7_published_festival_is_locked():
    published = FestivalScheduleInfo(**{**FESTIVAL.__dict__, "is_published": True})
    with pytest.raises(CannotModifyPublishedFestivalError):
        policy.ensure_festival_is_modifiable(published)
    policy.ensure_festival_is_modifiable(FESTIVAL)  # ne lève rien


@pytest.mark.parametrize("candidate", [
    TimeSlot(datetime(2027, 6, 18, 9), datetime(2027, 6, 18, 11)),    # commence avant l'ouverture
    TimeSlot(datetime(2027, 6, 20, 23), datetime(2027, 6, 21, 1)),    # finit après la clôture
    TimeSlot(datetime(2027, 7, 1, 18), datetime(2027, 7, 1, 19)),     # entièrement hors période
])
def test_r6_slot_outside_festival_is_rejected(candidate):
    with pytest.raises(ConcertOutsideFestivalError):
        policy.ensure_within_festival(candidate, FESTIVAL)


def test_r6_slot_on_festival_bounds_is_accepted():
    policy.ensure_within_festival(TimeSlot(FESTIVAL.start_date, FESTIVAL.end_date), FESTIVAL)


def test_r4_stage_of_another_festival_is_rejected():
    stage = Stage(id=100, festival_id=2, name="Ailleurs", capacity=100)
    artist = Artist(id=10, name="X", genre="Metal")
    with pytest.raises(StageNotInFestivalError):
        policy.ensure_stage_can_host(1, stage, artist)


def test_r5_missing_equipment_is_listed():
    stage = Stage(id=100, festival_id=1, name="Warzone", capacity=100, available_equipment=EquipmentSet.of(["special_lighting"]))
    artist = Artist(id=10, name="Iron Vow", genre="Heavy",
                    required_equipment=EquipmentSet.of(["large_rigging", "special_lighting"]))
    with pytest.raises(EquipmentMismatchError) as err:
        policy.ensure_stage_can_host(1, stage, artist)
    assert str(err.value) == "La scène Warzone ne dispose pas des équipements requis : large_rigging"


def test_r5_stage_with_all_equipment_is_accepted():
    stage = Stage(id=100, festival_id=1, name="Main", capacity=100, available_equipment=EquipmentSet.of(["large_rigging", "pyro"]))
    artist = Artist(id=10, name="Iron Vow", genre="Heavy", required_equipment=EquipmentSet.of(["large_rigging"]))
    policy.ensure_stage_can_host(1, stage, artist)


def test_r2_and_r3_conflicts_are_detected_among_several_concerts():
    planning = [concert(1, 10, 100, slot(18, 19)), concert(2, 20, 200, slot(20, 21))]
    with pytest.raises(StageOccupiedError):
        policy.ensure_no_conflict(concert(None, 30, 100, slot(18, 20)), planning)
    with pytest.raises(ArtistAlreadyBookedError):
        policy.ensure_no_conflict(concert(None, 20, 300, slot(20, 22)), planning)
    policy.ensure_no_conflict(concert(None, 30, 300, slot(18, 22)), planning)  # autre scène, autre artiste


def test_cancelled_concerts_do_not_block_the_slot():
    planning = [concert(1, 10, 100, slot(18, 19), status="cancelled")]
    policy.ensure_no_conflict(concert(None, 20, 100, slot(18, 19)), planning)
