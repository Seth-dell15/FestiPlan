from datetime import datetime

import pytest

from app.domain.events.operation_events import FestivalPublishedEvent, FestivalUnpublishedEvent
from app.domain.exceptions.operation_exceptions import FestivalAlreadyPublishedError, FestivalNotPublishedError
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


def test_publish_moves_festival_from_preparation_to_published():
    festival = make_festival()

    festival.publish()

    assert festival.status is FestivalStatus.PUBLISHED
    assert festival.is_published


def test_publish_returns_the_festival_published_event():
    event = make_festival(id=7).publish()

    assert isinstance(event, FestivalPublishedEvent)
    assert (event.festival_id, event.festival_name) == (7, "Hellforge Open Air")


def test_unpublish_moves_festival_back_to_preparation_and_returns_event():
    festival = make_festival(id=7)
    festival.publish()

    event = festival.unpublish()

    assert festival.status is FestivalStatus.PREPARATION
    assert isinstance(event, FestivalUnpublishedEvent)
    assert (event.festival_id, event.festival_name) == (7, "Hellforge Open Air")


def test_unpublishing_a_festival_in_preparation_is_refused():
    with pytest.raises(FestivalNotPublishedError):
        make_festival().unpublish()


def test_publishing_twice_is_refused():
    festival = make_festival()
    festival.publish()

    with pytest.raises(FestivalAlreadyPublishedError):
        festival.publish()
