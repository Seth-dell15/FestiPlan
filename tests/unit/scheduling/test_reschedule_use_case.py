from datetime import datetime
import pytest
from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.ports.repositories.festival_repository_port import FestivalScheduleInfo, IFestivalQueryPort
from app.domain.exceptions.scheduling_exceptions import (
    StageOccupiedError,
    ArtistAlreadyBookedError,
    ConcertNotFoundError,
    ConcertOutsideFestivalError,
    CannotModifyPublishedFestivalError,
)
from app.application.use_cases.scheduling.reschedule_concert import (
    RescheduleConcertUseCase,
    RescheduleConcertCommand,
)
from app.adapters.secondary.repositories.in_memory_concert_repository import InMemoryConcertRepository
from app.adapters.secondary.notifications.fake_notification_adapter import FakeNotificationAdapter


class FakeFestivalQueryAdapter(IFestivalQueryPort):
    def __init__(self, festivals: dict[int, FestivalScheduleInfo] | None = None):
        self.festivals = festivals or {}

    def get_schedule_info(self, festival_id: int) -> FestivalScheduleInfo | None:
        return self.festivals.get(festival_id)


@pytest.fixture
def festival_info():
    return FestivalScheduleInfo(
        id=1,
        name="Hellforge Open Air",
        start_date=datetime(2027, 6, 18, 10, 0),
        end_date=datetime(2027, 6, 20, 23, 59),
        is_published=False,
    )


@pytest.fixture
def concert_repo():
    # Concert 1 : Mainstage (100), Artiste 10 (Iron Vow), 18h - 19h
    c1 = Concert(
        id=1,
        festival_id=1,
        artist_id=10,
        stage_id=100,
        time_slot=TimeSlot(datetime(2027, 6, 18, 18, 0), datetime(2027, 6, 18, 19, 0)),
    )
    # Concert 2 : Mainstage (100), Artiste 20 (Crimson Engine), 19h30 - 20h30
    c2 = Concert(
        id=2,
        festival_id=1,
        artist_id=20,
        stage_id=100,
        time_slot=TimeSlot(datetime(2027, 6, 18, 19, 30), datetime(2027, 6, 18, 20, 30)),
    )
    # Concert 3 : Warzone (200), Artiste 10 (Iron Vow sur une autre scène le lendemain), 19 juin 21h - 22h
    c3 = Concert(
        id=3,
        festival_id=1,
        artist_id=10,
        stage_id=200,
        time_slot=TimeSlot(datetime(2027, 6, 19, 21, 0), datetime(2027, 6, 19, 22, 0)),
    )
    return InMemoryConcertRepository([c1, c2, c3])


def test_reschedule_success(concert_repo, festival_info):
    notifier = FakeNotificationAdapter()
    festival_adapter = FakeFestivalQueryAdapter({1: festival_info})
    use_case = RescheduleConcertUseCase(
        concert_repository=concert_repo,
        festival_query_port=festival_adapter,
        notification_sender=notifier,
    )

    cmd = RescheduleConcertCommand(
        concert_id=1,
        new_start=datetime(2027, 6, 18, 14, 0),
        new_end=datetime(2027, 6, 18, 15, 0),
    )
    result = use_case.execute(cmd)

    assert result.concert.time_slot.start == datetime(2027, 6, 18, 14, 0)
    assert result.notification_sent is True
    assert len(notifier.sent_notifications) == 1
    # Vérification que la persistance est bien à jour
    assert concert_repo.get_by_id(1).time_slot.start == datetime(2027, 6, 18, 14, 0)


def test_defect_1_stage_conflict_refused(concert_repo, festival_info):
    """Vérification du Défaut 1 : un déplacement créant un conflit de scène est refusé."""
    use_case = RescheduleConcertUseCase(
        concert_repository=concert_repo,
        festival_query_port=FakeFestivalQueryAdapter({1: festival_info}),
    )

    # Tentative de déplacer Concert 1 (sur Mainstage) pour chevaucher Concert 2 (19h30 - 20h30)
    cmd = RescheduleConcertCommand(
        concert_id=1,
        new_start=datetime(2027, 6, 18, 19, 45),
        new_end=datetime(2027, 6, 18, 20, 45),
    )

    with pytest.raises(StageOccupiedError):
        use_case.execute(cmd)

    # Vérification que le concert n'a PAS été modifié
    assert concert_repo.get_by_id(1).time_slot.start == datetime(2027, 6, 18, 18, 0)


def test_defect_1_artist_conflict_refused(concert_repo, festival_info):
    """Vérification du Défaut 1 : un artiste ne peut pas être déplacé sur un créneau où il joue déjà."""
    use_case = RescheduleConcertUseCase(
        concert_repository=concert_repo,
        festival_query_port=FakeFestivalQueryAdapter({1: festival_info}),
    )

    # Déplacer Concert 1 (Artiste 10) sur le créneau du 19 juin 21h où l'Artiste 10 joue déjà (Concert 3)
    cmd = RescheduleConcertCommand(
        concert_id=1,
        new_start=datetime(2027, 6, 19, 21, 30),
        new_end=datetime(2027, 6, 19, 22, 30),
    )

    with pytest.raises(ArtistAlreadyBookedError):
        use_case.execute(cmd)


def test_defect_2_notification_failure_does_not_break_persistence(concert_repo, festival_info):
    """Vérification du Défaut 2 : l'échec de notification ne corrompt pas l'opération métier."""
    failing_notifier = FakeNotificationAdapter(should_fail=True)
    use_case = RescheduleConcertUseCase(
        concert_repository=concert_repo,
        festival_query_port=FakeFestivalQueryAdapter({1: festival_info}),
        notification_sender=failing_notifier,
    )

    cmd = RescheduleConcertCommand(
        concert_id=1,
        new_start=datetime(2027, 6, 18, 14, 0),
        new_end=datetime(2027, 6, 18, 15, 0),
    )
    result = use_case.execute(cmd)

    # Le déplacement a réussi et a bien été enregistré
    assert result.concert.time_slot.start == datetime(2027, 6, 18, 14, 0)
    assert concert_repo.get_by_id(1).time_slot.start == datetime(2027, 6, 18, 14, 0)
    # L'erreur de notification est documentée sans lever d'exception 500 bloquante
    assert result.notification_sent is False
    assert "Simulation d'échec" in (result.notification_error or "")


def test_defect_3_cannot_reschedule_published_festival(concert_repo):
    """Vérification du Défaut 3 : un festival publié refuse le déplacement ordinaire."""
    published_festival = FestivalScheduleInfo(
        id=1,
        name="Hellforge Open Air",
        start_date=datetime(2027, 6, 18, 10, 0),
        end_date=datetime(2027, 6, 20, 23, 59),
        is_published=True,  # Festival publié !
    )
    use_case = RescheduleConcertUseCase(
        concert_repository=concert_repo,
        festival_query_port=FakeFestivalQueryAdapter({1: published_festival}),
    )

    cmd = RescheduleConcertCommand(
        concert_id=1,
        new_start=datetime(2027, 6, 18, 14, 0),
        new_end=datetime(2027, 6, 18, 15, 0),
    )

    with pytest.raises(CannotModifyPublishedFestivalError):
        use_case.execute(cmd)


def test_reschedule_outside_festival_dates_refused(concert_repo, festival_info):
    """Règle R6 : le concert doit rester dans les dates du festival."""
    use_case = RescheduleConcertUseCase(
        concert_repository=concert_repo,
        festival_query_port=FakeFestivalQueryAdapter({1: festival_info}),
    )

    # Déplacement au 25 juin (le festival finit le 20 juin)
    cmd = RescheduleConcertCommand(
        concert_id=1,
        new_start=datetime(2027, 6, 25, 18, 0),
        new_end=datetime(2027, 6, 25, 19, 0),
    )

    with pytest.raises(ConcertOutsideFestivalError):
        use_case.execute(cmd)


def test_reschedule_nonexistent_concert_raises_not_found(concert_repo, festival_info):
    use_case = RescheduleConcertUseCase(
        concert_repository=concert_repo,
        festival_query_port=FakeFestivalQueryAdapter({1: festival_info}),
    )

    cmd = RescheduleConcertCommand(
        concert_id=9999,
        new_start=datetime(2027, 6, 18, 14, 0),
        new_end=datetime(2027, 6, 18, 15, 0),
    )

    with pytest.raises(ConcertNotFoundError):
        use_case.execute(cmd)
