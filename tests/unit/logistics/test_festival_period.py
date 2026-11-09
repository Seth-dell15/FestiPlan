from datetime import datetime, timedelta, timezone

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


def test_mixed_timezone_dates_are_compared_in_utc():
    paris = timezone(timedelta(hours=2))

    period = FestivalPeriod(start=datetime(2027, 6, 18, 12, 0, tzinfo=paris), end=END)

    assert period.start == START
    assert period.start.tzinfo is None


def test_mixed_timezone_dates_are_still_validated():
    with pytest.raises(InvalidFestivalDatesError):
        FestivalPeriod(start=datetime(2027, 6, 18, 10, 0, tzinfo=timezone.utc), end=START)
