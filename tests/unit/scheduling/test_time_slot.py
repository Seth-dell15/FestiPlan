from datetime import datetime, timedelta
import pytest
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.exceptions.scheduling_exceptions import InvalidTimeSlotError


def test_valid_time_slot_creation():
    start = datetime(2027, 6, 18, 18, 0)
    end = datetime(2027, 6, 18, 19, 30)
    slot = TimeSlot(start=start, end=end)
    
    assert slot.start == start
    assert slot.end == end
    assert slot.duration == timedelta(minutes=90)


def test_time_slot_end_before_start_raises_error():
    start = datetime(2027, 6, 18, 19, 0)
    end = datetime(2027, 6, 18, 18, 0)
    
    with pytest.raises(InvalidTimeSlotError) as exc_info:
        TimeSlot(start=start, end=end)
    
    assert "Créneau invalide" in str(exc_info.value)


def test_time_slot_end_equal_to_start_raises_error():
    moment = datetime(2027, 6, 18, 18, 0)
    
    with pytest.raises(InvalidTimeSlotError):
        TimeSlot(start=moment, end=moment)


@pytest.mark.parametrize(
    "start_b, end_b, expected_overlap",
    [
        # Chevauchement partiel (B commence pendant A)
        (datetime(2027, 6, 18, 18, 30), datetime(2027, 6, 18, 19, 30), True),
        # Chevauchement partiel (B finit pendant A)
        (datetime(2027, 6, 18, 17, 30), datetime(2027, 6, 18, 18, 30), True),
        # B est complètement inclus dans A
        (datetime(2027, 6, 18, 18, 15), datetime(2027, 6, 18, 18, 45), True),
        # B englobe complètement A
        (datetime(2027, 6, 18, 17, 0), datetime(2027, 6, 18, 20, 0), True),
        # Strictement avant (disjoints)
        (datetime(2027, 6, 18, 16, 0), datetime(2027, 6, 18, 17, 0), False),
        # Strictement après (disjoints)
        (datetime(2027, 6, 18, 20, 0), datetime(2027, 6, 18, 21, 0), False),
        # Contigus : B commence exactement quand A finit -> PAS de chevauchement
        (datetime(2027, 6, 18, 19, 0), datetime(2027, 6, 18, 20, 0), False),
        # Contigus : B finit exactement quand A commence -> PAS de chevauchement
        (datetime(2027, 6, 18, 17, 0), datetime(2027, 6, 18, 18, 0), False),
    ],
)
def test_time_slot_overlaps(start_b, end_b, expected_overlap):
    slot_a = TimeSlot(
        start=datetime(2027, 6, 18, 18, 0),
        end=datetime(2027, 6, 18, 19, 0),
    )
    slot_b = TimeSlot(start=start_b, end=end_b)
    
    assert slot_a.overlaps(slot_b) is expected_overlap
    assert slot_b.overlaps(slot_a) is expected_overlap


def test_time_slot_is_within():
    slot = TimeSlot(
        start=datetime(2027, 6, 18, 18, 0),
        end=datetime(2027, 6, 18, 19, 0),
    )
    fest_start = datetime(2027, 6, 18, 10, 0)
    fest_end = datetime(2027, 6, 20, 23, 59)
    
    # Parfaitement inclus
    assert slot.is_within(fest_start, fest_end) is True
    
    # Commence avant le festival
    assert slot.is_within(datetime(2027, 6, 18, 18, 30), fest_end) is False
    
    # Finit après le festival
    assert slot.is_within(fest_start, datetime(2027, 6, 18, 18, 30)) is False
