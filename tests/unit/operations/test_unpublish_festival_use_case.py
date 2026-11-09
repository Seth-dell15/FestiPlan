from datetime import datetime

import pytest

from app.adapters.secondary.notifications.fake_notification_adapter import FakeNotificationAdapter
from app.adapters.secondary.repositories.in_memory_festival_repository import InMemoryFestivalRepository
from app.application.use_cases.operations.unpublish_festival import UnpublishFestivalUseCase
from app.domain.events.operation_events import FestivalUnpublishedEvent
from app.domain.exceptions.logistics_exceptions import FestivalNotFoundError
from app.domain.exceptions.operation_exceptions import FestivalNotPublishedError
from app.domain.models.festival import Festival
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.festival_status import FestivalStatus


def make_use_case(status=FestivalStatus.PUBLISHED, notification=None):
    festivals = InMemoryFestivalRepository([
        Festival(
            id=1,
            name="Hellforge",
            location="Clisson",
            period=FestivalPeriod(start=datetime(2027, 6, 18, 10), end=datetime(2027, 6, 20, 23)),
            status=status,
        )
    ])
    return UnpublishFestivalUseCase(festivals, notification or FakeNotificationAdapter()), festivals


def test_unpublish_reopens_the_schedule_and_notifies():
    notification = FakeNotificationAdapter()
    use_case, festivals = make_use_case(notification=notification)

    result = use_case.execute(1)

    assert result.notification_sent is True
    assert festivals.get_by_id(1).status is FestivalStatus.PREPARATION
    [event] = notification.sent_notifications
    assert isinstance(event, FestivalUnpublishedEvent)
    assert (event.festival_id, event.festival_name) == (1, "Hellforge")


def test_unpublish_unknown_festival_is_refused():
    use_case, _ = make_use_case()

    with pytest.raises(FestivalNotFoundError):
        use_case.execute(999)


def test_unpublish_festival_in_preparation_is_refused_without_notification():
    notification = FakeNotificationAdapter()
    use_case, _ = make_use_case(FestivalStatus.PREPARATION, notification)

    with pytest.raises(FestivalNotPublishedError):
        use_case.execute(1)

    assert notification.sent_notifications == []


def test_unpublish_survives_a_notification_failure():
    use_case, festivals = make_use_case(notification=FakeNotificationAdapter(should_fail=True))

    result = use_case.execute(1)

    assert result.notification_sent is False
    assert festivals.get_by_id(1).status is FestivalStatus.PREPARATION
