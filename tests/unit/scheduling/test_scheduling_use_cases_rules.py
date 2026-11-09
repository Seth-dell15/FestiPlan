"""Tests des cas d'utilisation Planification avec des adaptateurs en mémoire (R4, R5, R7, annulation)."""
from datetime import datetime
import pytest

from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.exceptions.logistics_exceptions import EquipmentMismatchError
from app.domain.models.artist import Artist
from app.domain.models.stage import Stage
from app.domain.value_objects.equipment_set import EquipmentSet
from app.domain.exceptions.scheduling_exceptions import (
    ArtistAlreadyBookedError,
    CannotModifyPublishedFestivalError,
    ConcertAlreadyCancelledError,
    StageNotInFestivalError,
    UnknownArtistError,
    UnknownFestivalError,
    UnknownStageError,
)
from app.application.use_cases.scheduling.schedule_concert import ScheduleConcertUseCase, ScheduleConcertCommand
from app.application.use_cases.scheduling.reschedule_concert import (
    RescheduleConcertUseCase,
    RescheduleConcertCommand,
)
from app.application.use_cases.scheduling.cancel_concert import CancelConcertUseCase
from app.adapters.secondary.repositories.in_memory_concert_query_adapter import InMemoryConcertQueryAdapter
from app.adapters.secondary.repositories.in_memory_artist_repository import InMemoryArtistRepository
from app.adapters.secondary.repositories.in_memory_stage_repository import InMemoryStageRepository
from app.adapters.secondary.notifications.fake_notification_adapter import FakeNotificationAdapter
from tests.unit.scheduling.test_reschedule_use_case import make_festival, make_schedules

STAGES = InMemoryStageRepository([
    Stage(id=100, festival_id=1, name="Mainstage", capacity=1000,
          available_equipment=EquipmentSet.of(["large_rigging", "special_lighting"])),
    Stage(id=200, festival_id=1, name="Warzone", capacity=500,
          available_equipment=EquipmentSet.of(["special_lighting"])),
    Stage(id=900, festival_id=2, name="Ailleurs", capacity=100),
])
ARTISTS = InMemoryArtistRepository([
    Artist(id=10, name="Iron Vow", genre="Heavy", required_equipment=EquipmentSet.of(["large_rigging"])),
    Artist(id=20, name="Concrete Reign", genre="Doom"),
])


def schedule(repo=None, published=False):
    repo = repo or InMemoryConcertQueryAdapter()
    return ScheduleConcertUseCase(make_schedules(repo, make_festival(published)), repo, STAGES, ARTISTS)


def cmd(**overrides):
    values = dict(festival_id=1, artist_id=20, stage_id=200,
                  start_time=datetime(2027, 6, 19, 10), end_time=datetime(2027, 6, 19, 11))
    values.update(overrides)
    return ScheduleConcertCommand(**values)


def existing_concert(status="scheduled"):
    return Concert(id=1, festival_id=1, artist_id=20, stage_id=200,
                   time_slot=TimeSlot(datetime(2027, 6, 19, 10), datetime(2027, 6, 19, 11)), status=status)


# --- Programmer : R4 / R5 / R7 ----------------------------------------------------

@pytest.mark.parametrize("overrides, error", [
    ({"festival_id": 99}, UnknownFestivalError),
    ({"stage_id": 99}, UnknownStageError),
    ({"artist_id": 99}, UnknownArtistError),
    ({"stage_id": 900}, StageNotInFestivalError),
    ({"artist_id": 10, "stage_id": 200}, EquipmentMismatchError),
])
def test_schedule_rejects_invalid_references_and_nothing_is_saved(overrides, error):
    repo = InMemoryConcertQueryAdapter()
    with pytest.raises(error):
        schedule(repo).execute(cmd(**overrides))
    assert repo.list_for_festival(1, include_cancelled=True) == []


def test_schedule_accepts_artist_on_stage_with_required_equipment():
    concert = schedule().execute(cmd(artist_id=10, stage_id=100))
    assert concert.id is not None


def test_schedule_is_refused_on_published_festival():
    with pytest.raises(CannotModifyPublishedFestivalError):
        schedule(published=True).execute(cmd())


# --- R3 entre festivals ------------------------------------------------------------

def booking_elsewhere(artist_id=20, status="scheduled"):
    return Concert(id=5, festival_id=2, artist_id=artist_id, stage_id=900,
                   time_slot=TimeSlot(datetime(2027, 6, 19, 10), datetime(2027, 6, 19, 11)), status=status)


def test_schedule_is_refused_when_artist_plays_in_another_festival():
    repo = InMemoryConcertQueryAdapter([booking_elsewhere()])
    with pytest.raises(ArtistAlreadyBookedError):
        schedule(repo).execute(cmd())
    assert repo.list_for_festival(1, include_cancelled=True) == []


@pytest.mark.parametrize("elsewhere", [
    booking_elsewhere(artist_id=10),
    booking_elsewhere(status="cancelled"),
], ids=["autre_artiste", "concert_annule"])
def test_schedule_is_accepted_when_the_booking_elsewhere_does_not_block(elsewhere):
    assert schedule(InMemoryConcertQueryAdapter([elsewhere])).execute(cmd()).id is not None


def test_reschedule_is_refused_when_artist_plays_in_another_festival():
    moved = Concert(id=1, festival_id=1, artist_id=20, stage_id=200,
                    time_slot=TimeSlot(datetime(2027, 6, 19, 14), datetime(2027, 6, 19, 15)))
    repo = InMemoryConcertQueryAdapter([moved, booking_elsewhere()])
    use_case = RescheduleConcertUseCase(make_schedules(repo), repo, FakeNotificationAdapter())

    with pytest.raises(ArtistAlreadyBookedError):
        use_case.execute(RescheduleConcertCommand(1, datetime(2027, 6, 19, 10), datetime(2027, 6, 19, 11)))

    assert repo.get_by_id(1).time_slot.start == datetime(2027, 6, 19, 14)


# --- Déplacer un concert annulé ---------------------------------------------------

def test_reschedule_cancelled_concert_is_refused_and_no_notification_is_sent():
    repo = InMemoryConcertQueryAdapter([existing_concert(status="cancelled")])
    notifier = FakeNotificationAdapter()
    use_case = RescheduleConcertUseCase(make_schedules(repo), repo, notifier)
    with pytest.raises(ConcertAlreadyCancelledError):
        use_case.execute(RescheduleConcertCommand(1, datetime(2027, 6, 19, 14), datetime(2027, 6, 19, 15)))
    assert notifier.sent_notifications == []


def test_reschedule_notifies_the_concert_rescheduled_event():
    repo = InMemoryConcertQueryAdapter([existing_concert()])
    notifier = FakeNotificationAdapter()
    RescheduleConcertUseCase(make_schedules(repo), repo, notifier).execute(
        RescheduleConcertCommand(1, datetime(2027, 6, 19, 14), datetime(2027, 6, 19, 15))
    )
    [event] = notifier.sent_notifications
    assert event.concert_id == 1
    assert event.previous_time_slot.start == datetime(2027, 6, 19, 10)
    assert event.new_time_slot.start == datetime(2027, 6, 19, 14)


# --- Annuler : R7 et double annulation -------------------------------------------

def test_cancel_is_refused_on_published_festival_and_concert_is_unchanged():
    repo = InMemoryConcertQueryAdapter([existing_concert()])
    with pytest.raises(CannotModifyPublishedFestivalError):
        CancelConcertUseCase(make_schedules(repo, make_festival(published=True))).execute(1)
    assert not repo.get_by_id(1).is_cancelled


def test_cancel_twice_is_refused():
    repo = InMemoryConcertQueryAdapter([existing_concert()])
    use_case = CancelConcertUseCase(make_schedules(repo))
    use_case.execute(1)
    with pytest.raises(ConcertAlreadyCancelledError):
        use_case.execute(1)
