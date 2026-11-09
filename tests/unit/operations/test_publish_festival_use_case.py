from datetime import datetime
import pytest

from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.ports.repositories.festival_repository_port import (
    IFestivalQueryPort,
    IFestivalCommandPort,
    FestivalScheduleInfo,
)
from app.domain.ports.services.notification_sender_port import INotificationSenderPort
from app.adapters.secondary.repositories.in_memory_concert_repository import (
    InMemoryConcertRepository,
)
from app.application.use_cases.operations.publish_festival import (
    PublishFestivalUseCase,
)
from app.domain.exceptions.operation_exceptions import (
    FestivalNotFoundError,
    FestivalAlreadyPublishedError,
    CannotPublishInvalidScheduleError,
)


class FakeFestivalAdapter(IFestivalQueryPort, IFestivalCommandPort):
    def __init__(self, festivals: dict[int, FestivalScheduleInfo] | None = None) -> None:
        self.festivals = festivals or {}

    def get_schedule_info(self, festival_id: int) -> FestivalScheduleInfo | None:
        return self.festivals.get(festival_id)

    def publish_festival(self, festival_id: int) -> FestivalScheduleInfo | None:
        fest = self.festivals.get(festival_id)
        if not fest:
            return None
        updated = FestivalScheduleInfo(
            id=fest.id,
            name=fest.name,
            start_date=fest.start_date,
            end_date=fest.end_date,
            is_published=True,
        )
        self.festivals[festival_id] = updated
        return updated


class FakeNotificationAdapter(INotificationSenderPort):
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.sent_messages: list[tuple[int, str]] = []

    def notify_schedule_change(self, festival_id: int, message: str) -> bool:
        if self.should_fail:
            raise RuntimeError("Simulation de panne réseau d'envoi d'e-mail.")
        self.sent_messages.append((festival_id, message))
        return True


@pytest.fixture
def festival_dates():
    return {
        "start": datetime(2027, 6, 18, 10, 0),
        "end": datetime(2027, 6, 20, 23, 0),
    }


def test_publish_festival_not_found_raises_error():
    fest_adapter = FakeFestivalAdapter()
    concert_repo = InMemoryConcertRepository()
    notif = FakeNotificationAdapter()
    uc = PublishFestivalUseCase(fest_adapter, fest_adapter, concert_repo, notif)

    with pytest.raises(FestivalNotFoundError):
        uc.execute(festival_id=999)


def test_publish_already_published_festival_raises_error(festival_dates):
    fest_info = FestivalScheduleInfo(
        id=1,
        name="Hellforge",
        start_date=festival_dates["start"],
        end_date=festival_dates["end"],
        is_published=True,
    )
    fest_adapter = FakeFestivalAdapter({1: fest_info})
    concert_repo = InMemoryConcertRepository()
    notif = FakeNotificationAdapter()
    uc = PublishFestivalUseCase(fest_adapter, fest_adapter, concert_repo, notif)

    with pytest.raises(FestivalAlreadyPublishedError):
        uc.execute(festival_id=1)


def test_publish_with_concert_outside_festival_dates_raises_r8_error(festival_dates):
    fest_info = FestivalScheduleInfo(
        id=1,
        name="Hellforge",
        start_date=festival_dates["start"],
        end_date=festival_dates["end"],
        is_published=False,
    )
    fest_adapter = FakeFestivalAdapter({1: fest_info})
    # Concert qui déborde après la fin du festival
    concert_repo = InMemoryConcertRepository([
        Concert(
            festival_id=1,
            artist_id=1,
            stage_id=1,
            time_slot=TimeSlot(
                start=datetime(2027, 6, 21, 0, 0),
                end=datetime(2027, 6, 21, 1, 0),
            ),
        )
    ])
    notif = FakeNotificationAdapter()
    uc = PublishFestivalUseCase(fest_adapter, fest_adapter, concert_repo, notif)

    with pytest.raises(CannotPublishInvalidScheduleError, match="déborde des dates"):
        uc.execute(festival_id=1)


def test_publish_with_stage_conflict_raises_r8_error(festival_dates):
    fest_info = FestivalScheduleInfo(
        id=1,
        name="Hellforge",
        start_date=festival_dates["start"],
        end_date=festival_dates["end"],
        is_published=False,
    )
    fest_adapter = FakeFestivalAdapter({1: fest_info})
    # Deux concerts différents sur la même scène au même créneau
    slot = TimeSlot(
        start=datetime(2027, 6, 18, 14, 0),
        end=datetime(2027, 6, 18, 15, 0),
    )
    concert_repo = InMemoryConcertRepository([
        Concert(festival_id=1, artist_id=1, stage_id=1, time_slot=slot),
        Concert(festival_id=1, artist_id=2, stage_id=1, time_slot=slot),
    ])
    notif = FakeNotificationAdapter()
    uc = PublishFestivalUseCase(fest_adapter, fest_adapter, concert_repo, notif)

    with pytest.raises(CannotPublishInvalidScheduleError, match="conflit de programmation"):
        uc.execute(festival_id=1)


def test_publish_with_artist_conflict_raises_r8_error(festival_dates):
    fest_info = FestivalScheduleInfo(
        id=1,
        name="Hellforge",
        start_date=festival_dates["start"],
        end_date=festival_dates["end"],
        is_published=False,
    )
    fest_adapter = FakeFestivalAdapter({1: fest_info})
    # Même artiste sur deux scènes différentes au même créneau
    slot = TimeSlot(
        start=datetime(2027, 6, 18, 14, 0),
        end=datetime(2027, 6, 18, 15, 0),
    )
    concert_repo = InMemoryConcertRepository([
        Concert(festival_id=1, artist_id=1, stage_id=1, time_slot=slot),
        Concert(festival_id=1, artist_id=1, stage_id=2, time_slot=slot),
    ])
    notif = FakeNotificationAdapter()
    uc = PublishFestivalUseCase(fest_adapter, fest_adapter, concert_repo, notif)

    with pytest.raises(CannotPublishInvalidScheduleError, match="conflit de programmation"):
        uc.execute(festival_id=1)


def test_publish_nominal_success(festival_dates):
    fest_info = FestivalScheduleInfo(
        id=1,
        name="Hellforge",
        start_date=festival_dates["start"],
        end_date=festival_dates["end"],
        is_published=False,
    )
    fest_adapter = FakeFestivalAdapter({1: fest_info})
    concert_repo = InMemoryConcertRepository([
        Concert(
            festival_id=1,
            artist_id=1,
            stage_id=1,
            time_slot=TimeSlot(
                start=datetime(2027, 6, 18, 14, 0),
                end=datetime(2027, 6, 18, 15, 0),
            ),
        ),
        Concert(
            festival_id=1,
            artist_id=2,
            stage_id=2,
            time_slot=TimeSlot(
                start=datetime(2027, 6, 18, 14, 0),
                end=datetime(2027, 6, 18, 15, 0),
            ),
        ),
    ])
    notif = FakeNotificationAdapter()
    uc = PublishFestivalUseCase(fest_adapter, fest_adapter, concert_repo, notif)

    result = uc.execute(festival_id=1)

    assert result.festival.is_published is True
    assert result.notification_sent is True
    assert len(notif.sent_messages) == 1


def test_publish_with_notification_failure_still_publishes(festival_dates):
    fest_info = FestivalScheduleInfo(
        id=1,
        name="Hellforge",
        start_date=festival_dates["start"],
        end_date=festival_dates["end"],
        is_published=False,
    )
    fest_adapter = FakeFestivalAdapter({1: fest_info})
    concert_repo = InMemoryConcertRepository()
    # Notification simule une panne
    failing_notif = FakeNotificationAdapter(should_fail=True)
    uc = PublishFestivalUseCase(fest_adapter, fest_adapter, concert_repo, failing_notif)

    result = uc.execute(festival_id=1)

    # La publication a réussi malgré la panne d'email (Résolution Défaut 2)
    assert result.festival.is_published is True
    assert result.notification_sent is False
