from datetime import datetime
import pytest

from app.adapters.secondary.notifications.fake_notification_adapter import FakeNotificationAdapter
from app.adapters.secondary.repositories.in_memory_artist_repository import InMemoryArtistRepository
from app.adapters.secondary.repositories.in_memory_concert_repository import InMemoryConcertRepository
from app.adapters.secondary.repositories.in_memory_festival_repository import InMemoryFestivalRepository
from app.adapters.secondary.repositories.in_memory_stage_repository import InMemoryStageRepository
from app.application.use_cases.operations.publish_festival import PublishFestivalUseCase
from app.domain.exceptions.logistics_exceptions import FestivalNotFoundError
from app.domain.exceptions.operation_exceptions import (
    CannotPublishInvalidScheduleError,
    FestivalAlreadyPublishedError,
)
from app.domain.models.artist import Artist
from app.domain.models.concert import Concert
from app.domain.models.festival import Festival
from app.domain.events.operation_events import FestivalPublishedEvent
from app.domain.models.stage import Stage
from app.domain.value_objects.concert_status import ConcertStatus
from app.domain.value_objects.equipment_set import EquipmentSet
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.festival_status import FestivalStatus
from app.domain.value_objects.time_slot import TimeSlot

SLOT = TimeSlot(start=datetime(2027, 6, 18, 14, 0), end=datetime(2027, 6, 18, 15, 0))
OUTSIDE_FESTIVAL = TimeSlot(start=datetime(2027, 6, 21, 0, 0), end=datetime(2027, 6, 21, 1, 0))


def make_festival(status=FestivalStatus.PREPARATION):
    return Festival(
        id=1,
        name="Hellforge",
        location="Clisson",
        period=FestivalPeriod(start=datetime(2027, 6, 18, 10, 0), end=datetime(2027, 6, 20, 23, 0)),
        status=status,
    )


def make_use_case(festivals=(), concerts=(), notification=None):
    festival_repository = InMemoryFestivalRepository(list(festivals))
    use_case = PublishFestivalUseCase(
        festival_repository,
        InMemoryConcertRepository(list(concerts)),
        InMemoryStageRepository([
            Stage(id=1, festival_id=1, name="Mainstage", capacity=1000, available_equipment=EquipmentSet.of(["pyro"])),
            Stage(id=2, festival_id=1, name="Warzone", capacity=500),
            Stage(id=9, festival_id=2, name="Ailleurs", capacity=100),
        ]),
        InMemoryArtistRepository([
            Artist(id=1, name="Iron Vow", genre="Heavy", required_equipment=EquipmentSet.of(["pyro"])),
            Artist(id=2, name="Abyss", genre="Doom"),
        ]),
        notification or FakeNotificationAdapter(),
    )
    return use_case, festival_repository


def concert(artist_id=2, stage_id=2, time_slot=SLOT):
    return Concert(festival_id=1, artist_id=artist_id, stage_id=stage_id, time_slot=time_slot)


def test_publish_festival_not_found_raises_error():
    use_case, _ = make_use_case()

    with pytest.raises(FestivalNotFoundError):
        use_case.execute(festival_id=999)


def test_publish_already_published_festival_raises_error():
    use_case, _ = make_use_case([make_festival(FestivalStatus.PUBLISHED)], [concert()])

    with pytest.raises(FestivalAlreadyPublishedError):
        use_case.execute(festival_id=1)


@pytest.mark.parametrize(
    "concerts",
    [[], [Concert(festival_id=1, artist_id=2, stage_id=2, time_slot=SLOT, status=ConcertStatus.CANCELLED)]],
    ids=["aucun_concert", "uniquement_des_annules"],
)
def test_publish_empty_schedule_is_refused(concerts):
    notification = FakeNotificationAdapter()
    use_case, festivals = make_use_case([make_festival()], concerts, notification)

    with pytest.raises(CannotPublishInvalidScheduleError, match="sans concert"):
        use_case.execute(festival_id=1)

    assert festivals.get_by_id(1).status is FestivalStatus.PREPARATION
    assert notification.sent_notifications == []


@pytest.mark.parametrize(
    "concerts, message",
    [
        ([concert(time_slot=OUTSIDE_FESTIVAL)], "déborde des dates"),
        ([concert(artist_id=2, stage_id=2), concert(artist_id=1, stage_id=2)], "conflit de programmation"),
        ([concert(artist_id=2, stage_id=2), concert(artist_id=2, stage_id=1)], "conflit de programmation"),
        ([concert(artist_id=99)], "inconnu"),
        ([concert(stage_id=99)], "inconnu"),
        ([concert(stage_id=9)], "n'appartient pas"),
        ([concert(artist_id=1, stage_id=2)], "équipements requis"),
    ],
    ids=["R6", "R2", "R3", "R4_artiste", "R4_scene", "R4_autre_festival", "R5"],
)
def test_publish_with_invalid_schedule_is_refused_and_stays_in_preparation(concerts, message):
    use_case, festivals = make_use_case([make_festival()], concerts)

    with pytest.raises(CannotPublishInvalidScheduleError, match=message):
        use_case.execute(festival_id=1)

    assert festivals.get_by_id(1).status is FestivalStatus.PREPARATION


def test_publish_nominal_success():
    notification = FakeNotificationAdapter()
    concerts = [concert(artist_id=1, stage_id=1), concert(artist_id=2, stage_id=2)]
    use_case, festivals = make_use_case([make_festival()], concerts, notification)

    result = use_case.execute(festival_id=1)

    assert result.festival.is_published is True
    assert festivals.get_by_id(1).is_published is True
    assert result.notification_sent is True
    [event] = notification.sent_notifications
    assert isinstance(event, FestivalPublishedEvent)
    assert (event.festival_id, event.festival_name) == (1, "Hellforge")


def test_publish_with_notification_failure_still_publishes():
    use_case, festivals = make_use_case(
        [make_festival()], [concert()], notification=FakeNotificationAdapter(should_fail=True)
    )

    result = use_case.execute(festival_id=1)

    # La publication a réussi malgré la panne d'email (Résolution Défaut 2)
    assert result.festival.is_published is True
    assert festivals.get_by_id(1).is_published is True
    assert result.notification_sent is False
