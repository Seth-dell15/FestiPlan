from datetime import datetime

import pytest

from app.domain.exceptions.logistics_exceptions import InvalidFestivalDatesError
from app.domain.value_objects.festival_period import FestivalPeriod

START = datetime(2027, 6, 18, 10, 0)
END = datetime(2027, 6, 20, 23, 59)


def test_end_must_be_after_start():
    with pytest.raises(InvalidFestivalDatesError):
        FestivalPeriod(start=END, end=START)


def test_end_equal_to_start_is_rejected():
    with pytest.raises(InvalidFestivalDatesError):
        FestivalPeriod(start=START, end=START)


def test_contains_a_slot_inside_the_period():
    period = FestivalPeriod(start=START, end=END)
    assert period.contains(datetime(2027, 6, 18, 18, 0), datetime(2027, 6, 18, 19, 0))


def test_contains_a_slot_on_the_exact_bounds():
    period = FestivalPeriod(start=START, end=END)
    assert period.contains(START, END)


@pytest.mark.parametrize(
    "start, end",
    [
        (datetime(2027, 6, 18, 9, 0), datetime(2027, 6, 18, 11, 0)),
        (datetime(2027, 6, 20, 23, 0), datetime(2027, 6, 21, 0, 30)),
        (datetime(2027, 6, 21, 18, 0), datetime(2027, 6, 21, 19, 0)),
    ],
)
def test_does_not_contain_a_slot_overflowing_the_period(start, end):
    assert not FestivalPeriod(start=START, end=END).contains(start, end)
