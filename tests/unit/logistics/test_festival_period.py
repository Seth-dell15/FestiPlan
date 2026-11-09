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
