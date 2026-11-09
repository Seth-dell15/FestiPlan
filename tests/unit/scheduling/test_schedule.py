"""Tests unitaires du domaine Planification : sans FastAPI ni base de données."""
from datetime import datetime, timedelta, timezone
import pytest

from app.domain.models.concert import Concert
from app.domain.models.schedule import Schedule
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.exceptions.logistics_exceptions import EquipmentMismatchError
from app.domain.models.artist import Artist
from app.domain.models.stage import Stage
from app.domain.value_objects.equipment_set import EquipmentSet
from app.domain.exceptions.scheduling_exceptions import (
    ArtistAlreadyBookedError,
    CannotModifyPublishedFestivalError,
    ConcertAlreadyCancelledError,
    ConcertNotFoundError,
    ConcertOutsideFestivalError,
    InvalidTimeSlotError,
    StageNotInFestivalError,
    StageOccupiedError,
)

PERIOD = FestivalPeriod(start=datetime(2027, 6, 18, 10), end=datetime(2027, 6, 20, 23, 59))
MAIN = Stage(id=100, festival_id=1, name="Mainstage", capacity=1000)
WARZONE = Stage(id=200, festival_id=1, name="Warzone", capacity=500)
VALLEY = Stage(id=300, festival_id=1, name="Valley", capacity=300)
IRON_VOW = Artist(id=10, name="Iron Vow", genre="Heavy")
ABYSS = Artist(id=20, name="Abyss", genre="Doom")
NOVA = Artist(id=30, name="Nova", genre="Thrash")


def slot(h1, h2, day=18):
    return TimeSlot(datetime(2027, 6, day, h1), datetime(2027, 6, day, h2))


def concert(cid, artist, stage, s, status="scheduled", festival=1):
    return Concert(id=cid, festival_id=festival, artist_id=artist, stage_id=stage, time_slot=s, status=status)


def schedule(*concerts, published=False):
    return Schedule(festival_id=1, period=PERIOD, is_published=published, concerts=list(concerts))


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
    assert s.start == datetime(2027, 6, 18, 18)
    assert s.start.tzinfo is None
    # comparable aux dates naïves stockées en base, sans TypeError
    assert s.overlaps(slot(18, 19))
    assert s.is_within(PERIOD.start, PERIOD.end)


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


# --- Schedule : programmer un concert (R2 à R7) -----------------------------------

def test_accepted_concert_joins_the_schedule():
    planning = schedule()
    added = planning.add_concert(IRON_VOW, MAIN, slot(18, 19))
    assert planning.concerts == [added]
    assert (added.festival_id, added.artist_id, added.stage_id) == (1, 10, 100)
    assert not added.is_cancelled


def test_r7_published_festival_is_locked():
    published = schedule(concert(1, 10, 100, slot(18, 19)), published=True)
    with pytest.raises(CannotModifyPublishedFestivalError):
        published.add_concert(ABYSS, WARZONE, slot(20, 21))
    with pytest.raises(CannotModifyPublishedFestivalError):
        published.reschedule_concert(1, slot(20, 21))
    with pytest.raises(CannotModifyPublishedFestivalError):
        published.cancel_concert(1)
    assert published.get_concert(1).time_slot == slot(18, 19)
    assert not published.get_concert(1).is_cancelled


@pytest.mark.parametrize("candidate", [
    TimeSlot(datetime(2027, 6, 18, 9), datetime(2027, 6, 18, 11)),    # commence avant l'ouverture
    TimeSlot(datetime(2027, 6, 20, 23), datetime(2027, 6, 21, 1)),    # finit après la clôture
    TimeSlot(datetime(2027, 7, 1, 18), datetime(2027, 7, 1, 19)),     # entièrement hors période
])
def test_r6_slot_outside_festival_is_rejected(candidate):
    planning = schedule(concert(1, 10, 100, slot(18, 19)))
    with pytest.raises(ConcertOutsideFestivalError):
        planning.add_concert(ABYSS, WARZONE, candidate)
    with pytest.raises(ConcertOutsideFestivalError):
        planning.reschedule_concert(1, candidate)
    assert len(planning.concerts) == 1


def test_r6_slot_on_festival_bounds_is_accepted():
    schedule().add_concert(IRON_VOW, MAIN, TimeSlot(PERIOD.start, PERIOD.end))


def test_r4_stage_of_another_festival_is_rejected():
    elsewhere = Stage(id=900, festival_id=2, name="Ailleurs", capacity=100)
    planning = schedule()
    with pytest.raises(StageNotInFestivalError):
        planning.add_concert(IRON_VOW, elsewhere, slot(18, 19))
    assert planning.concerts == []


def test_r5_missing_equipment_is_listed():
    stage = Stage(id=100, festival_id=1, name="Warzone", capacity=100,
                  available_equipment=EquipmentSet.of(["special_lighting"]))
    artist = Artist(id=10, name="Iron Vow", genre="Heavy",
                    required_equipment=EquipmentSet.of(["large_rigging", "special_lighting"]))
    with pytest.raises(EquipmentMismatchError) as err:
        schedule().add_concert(artist, stage, slot(18, 19))
    assert str(err.value) == "La scène Warzone ne dispose pas des équipements requis : large_rigging"


def test_r5_stage_with_all_equipment_is_accepted():
    stage = Stage(id=100, festival_id=1, name="Main", capacity=100,
                  available_equipment=EquipmentSet.of(["large_rigging", "pyro"]))
    artist = Artist(id=10, name="Iron Vow", genre="Heavy", required_equipment=EquipmentSet.of(["large_rigging"]))
    schedule().add_concert(artist, stage, slot(18, 19))


def test_r2_and_r3_conflicts_are_detected_among_several_concerts():
    planning = schedule(concert(1, 10, 100, slot(18, 19)), concert(2, 20, 200, slot(20, 21)))
    with pytest.raises(StageOccupiedError):
        planning.add_concert(NOVA, MAIN, slot(18, 20))
    with pytest.raises(ArtistAlreadyBookedError):
        planning.add_concert(ABYSS, VALLEY, slot(20, 22))
    assert len(planning.concerts) == 2
    planning.add_concert(NOVA, VALLEY, slot(18, 22))  # autre scène, autre artiste
    assert len(planning.concerts) == 3


def test_cancelled_concerts_do_not_block_the_slot():
    planning = schedule(concert(1, 10, 100, slot(18, 19), status="cancelled"))
    planning.add_concert(ABYSS, MAIN, slot(18, 19))


def test_r3_artist_booked_in_another_festival_is_rejected():
    elsewhere = [concert(9, 10, 900, slot(18, 19), festival=2)]
    planning = schedule(concert(1, 10, 100, slot(14, 15)))
    with pytest.raises(ArtistAlreadyBookedError):
        planning.add_concert(IRON_VOW, WARZONE, slot(18, 19), elsewhere)
    with pytest.raises(ArtistAlreadyBookedError):
        planning.reschedule_concert(1, slot(18, 19), elsewhere)
    assert planning.get_concert(1).time_slot == slot(14, 15)


# --- Schedule : déplacer et annuler ------------------------------------------------

def test_reschedule_moves_the_concert_and_returns_the_event():
    planning = schedule(concert(1, 10, 100, slot(18, 19)))
    event = planning.reschedule_concert(1, slot(20, 21))
    assert planning.get_concert(1).time_slot == slot(20, 21)
    assert (event.concert_id, event.previous_time_slot, event.new_time_slot) == (1, slot(18, 19), slot(20, 21))


def test_reschedule_conflict_leaves_the_concert_unchanged():
    planning = schedule(concert(1, 10, 100, slot(18, 19)), concert(2, 20, 100, slot(20, 21)))
    with pytest.raises(StageOccupiedError):
        planning.reschedule_concert(1, slot(20, 21))
    assert planning.get_concert(1).time_slot == slot(18, 19)


def test_reschedule_does_not_conflict_with_the_concert_itself():
    planning = schedule(concert(1, 10, 100, slot(18, 20)))
    planning.reschedule_concert(1, slot(19, 21))
    assert planning.get_concert(1).time_slot == slot(19, 21)


def test_reschedule_cancelled_concert_is_refused():
    planning = schedule(concert(1, 10, 100, slot(18, 19), status="cancelled"))
    with pytest.raises(ConcertAlreadyCancelledError):
        planning.reschedule_concert(1, slot(20, 21))


def test_cancel_frees_the_slot_and_keeps_the_concert_in_the_schedule():
    planning = schedule(concert(1, 10, 100, slot(18, 19)))
    cancelled = planning.cancel_concert(1)
    assert cancelled.is_cancelled
    assert planning.concerts == [cancelled]
    planning.add_concert(ABYSS, MAIN, slot(18, 19))


@pytest.mark.parametrize("operation", [
    lambda planning: planning.get_concert(42),
    lambda planning: planning.reschedule_concert(42, slot(20, 21)),
    lambda planning: planning.cancel_concert(42),
], ids=["consulter", "deplacer", "annuler"])
def test_unknown_concert_is_not_found(operation):
    with pytest.raises(ConcertNotFoundError):
        operation(schedule(concert(1, 10, 100, slot(18, 19))))


def test_active_concerts_are_chronological_without_cancelled():
    planning = schedule(
        concert(1, 10, 100, slot(20, 21)),
        concert(2, 20, 100, slot(14, 15)),
        concert(3, 30, 100, slot(16, 17), status="cancelled"),
    )
    assert [c.id for c in planning.active_concerts] == [2, 1]
