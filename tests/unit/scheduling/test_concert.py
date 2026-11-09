from datetime import datetime
import pytest
from app.domain.models.concert import Concert
from app.domain.value_objects.concert_status import ConcertStatus
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.exceptions.scheduling_exceptions import (
    StageOccupiedError,
    ArtistAlreadyBookedError,
)


def make_concert(
    concert_id: int = 1,
    artist_id: int = 10,
    stage_id: int = 100,
    start: str = "2027-06-18T18:00:00",
    end: str = "2027-06-18T19:00:00",
    status: str = "scheduled",
) -> Concert:
    return Concert(
        id=concert_id,
        festival_id=1,
        artist_id=artist_id,
        stage_id=stage_id,
        time_slot=TimeSlot(
            start=datetime.fromisoformat(start),
            end=datetime.fromisoformat(end),
        ),
        status=status,
    )


def test_concert_creation_and_reschedule():
    concert = make_concert()
    new_slot = TimeSlot(
        start=datetime(2027, 6, 18, 20, 0),
        end=datetime(2027, 6, 18, 21, 0),
    )
    
    event = concert.reschedule(new_slot)
    
    assert concert.time_slot == new_slot
    assert event.concert_id == concert.id
    assert event.new_time_slot == new_slot


def test_cannot_reschedule_cancelled_concert():
    concert = make_concert(status="cancelled")
    new_slot = TimeSlot(
        start=datetime(2027, 6, 18, 20, 0),
        end=datetime(2027, 6, 18, 21, 0),
    )
    
    with pytest.raises(ValueError, match="Impossible de déplacer un concert annulé"):
        concert.reschedule(new_slot)


def test_cancel_concert():
    concert = make_concert()
    assert not concert.is_cancelled
    
    concert.cancel()
    assert concert.is_cancelled
    assert concert.status is ConcertStatus.CANCELLED


def test_two_concerts_with_same_values_are_distinct_entities():
    first, second = make_concert(concert_id=None), make_concert(concert_id=None)
    assert first != second


def test_unknown_status_is_refused_at_creation():
    with pytest.raises(ValueError):
        make_concert(status="n_importe_quoi")


def test_unknown_status_is_refused_on_assignment():
    concert = make_concert()

    with pytest.raises(ValueError):
        concert.status = "n_importe_quoi"

    assert concert.status is ConcertStatus.SCHEDULED


def test_status_values_match_legacy_database_strings():
    assert ConcertStatus("scheduled") is ConcertStatus.SCHEDULED
    assert ConcertStatus("cancelled") is ConcertStatus.CANCELLED


def test_conflict_on_same_stage_raises_stage_occupied_error():
    # Concert A : Scène 100, Artiste 10, 18h-19h
    concert_a = make_concert(
        concert_id=1, stage_id=100, artist_id=10, start="2027-06-18T18:00:00", end="2027-06-18T19:00:00"
    )
    # Concert B : Même Scène 100, Artiste 20, 18h30-19h30 (chevauchement)
    concert_b = make_concert(
        concert_id=2, stage_id=100, artist_id=20, start="2027-06-18T18:30:00", end="2027-06-18T19:30:00"
    )
    
    with pytest.raises(StageOccupiedError) as exc_info:
        concert_a.check_conflict_with(concert_b)
    
    assert "Conflit de scène" in str(exc_info.value)


def test_conflict_with_same_artist_raises_artist_already_booked_error():
    # Concert A : Scène 100, Artiste 10, 18h-19h
    concert_a = make_concert(
        concert_id=1, stage_id=100, artist_id=10, start="2027-06-18T18:00:00", end="2027-06-18T19:00:00"
    )
    # Concert B : Scène 200, Même Artiste 10, 18h30-19h30 (chevauchement sur autre scène)
    concert_b = make_concert(
        concert_id=2, stage_id=200, artist_id=10, start="2027-06-18T18:30:00", end="2027-06-18T19:30:00"
    )
    
    with pytest.raises(ArtistAlreadyBookedError) as exc_info:
        concert_a.check_conflict_with(concert_b)
    
    assert "Conflit d'artiste" in str(exc_info.value)


def test_no_conflict_when_different_stages_and_artists():
    concert_a = make_concert(
        concert_id=1, stage_id=100, artist_id=10, start="2027-06-18T18:00:00", end="2027-06-18T19:00:00"
    )
    concert_b = make_concert(
        concert_id=2, stage_id=200, artist_id=20, start="2027-06-18T18:00:00", end="2027-06-18T19:00:00"
    )
    
    # Doit s'exécuter sans lever d'exception
    concert_a.check_conflict_with(concert_b)


def test_no_conflict_with_self():
    concert_a = make_concert(concert_id=1, stage_id=100, artist_id=10)
    concert_a.check_conflict_with(concert_a)


def test_no_conflict_if_one_is_cancelled():
    concert_a = make_concert(
        concert_id=1, stage_id=100, artist_id=10, start="2027-06-18T18:00:00", end="2027-06-18T19:00:00"
    )
    concert_b = make_concert(
        concert_id=2,
        stage_id=100,
        artist_id=20,
        start="2027-06-18T18:00:00",
        end="2027-06-18T19:00:00",
        status="cancelled",
    )
    
    concert_a.check_conflict_with(concert_b)
