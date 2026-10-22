from datetime import datetime

from app.domain.models.festival import Festival
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.festival_status import FestivalStatus


def make_festival(**overrides):
    values = dict(
        name="Hellforge Open Air",
        location="Clisson-sur-Rivière",
        period=FestivalPeriod(start=datetime(2027, 6, 18, 10, 0), end=datetime(2027, 6, 20, 23, 59)),
    )
    values.update(overrides)
    return Festival(**values)


def test_new_festival_is_in_preparation():
    festival = make_festival()
    assert festival.status is FestivalStatus.PREPARATION
    assert not festival.is_published


def test_status_values_match_legacy_database_strings():
    assert FestivalStatus("preparation") is FestivalStatus.PREPARATION
    assert FestivalStatus("published") is FestivalStatus.PUBLISHED


def test_two_festivals_with_same_values_are_distinct_entities():
    first, second = make_festival(), make_festival()
    assert first != second
