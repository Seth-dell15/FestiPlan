from datetime import datetime
import pytest
from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.ports.repositories.festival_repository_port import FestivalScheduleInfo
from app.domain.exceptions.scheduling_exceptions import (
    StageOccupiedError,
    ConcertNotFoundError,
)
from app.application.use_cases.scheduling.schedule_concert import (
    ScheduleConcertUseCase,
    ScheduleConcertCommand,
)
from app.application.use_cases.scheduling.cancel_concert import CancelConcertUseCase
from app.application.use_cases.scheduling.get_schedule import GetFestivalScheduleUseCase
from app.adapters.secondary.repositories.in_memory_concert_repository import InMemoryConcertRepository
from tests.unit.scheduling.test_reschedule_use_case import FakeFestivalQueryAdapter


@pytest.fixture
def festival_info():
    return FestivalScheduleInfo(
        id=1,
        name="Hellforge Open Air",
        start_date=datetime(2027, 6, 18, 10, 0),
        end_date=datetime(2027, 6, 20, 23, 59),
        is_published=False,
    )


def test_schedule_concert_success(festival_info):
    repo = InMemoryConcertRepository()
    use_case = ScheduleConcertUseCase(
        concert_repository=repo,
        festival_query_port=FakeFestivalQueryAdapter({1: festival_info}),
    )

    cmd = ScheduleConcertCommand(
        festival_id=1,
        artist_id=10,
        stage_id=100,
        start_time=datetime(2027, 6, 18, 18, 0),
        end_time=datetime(2027, 6, 18, 19, 0),
    )
    concert = use_case.execute(cmd)

    assert concert.id is not None
    assert concert.status == "scheduled"
    assert repo.get_by_id(concert.id) is not None


def test_schedule_concert_conflict_raises_stage_occupied(festival_info):
    existing = Concert(
        id=1,
        festival_id=1,
        artist_id=10,
        stage_id=100,
        time_slot=TimeSlot(datetime(2027, 6, 18, 18, 0), datetime(2027, 6, 18, 19, 0)),
    )
    repo = InMemoryConcertRepository([existing])
    use_case = ScheduleConcertUseCase(
        concert_repository=repo,
        festival_query_port=FakeFestivalQueryAdapter({1: festival_info}),
    )

    cmd = ScheduleConcertCommand(
        festival_id=1,
        artist_id=20,
        stage_id=100,
        start_time=datetime(2027, 6, 18, 18, 30),
        end_time=datetime(2027, 6, 18, 19, 30),
    )

    with pytest.raises(StageOccupiedError):
        use_case.execute(cmd)


def test_cancel_concert():
    concert = Concert(
        id=1,
        festival_id=1,
        artist_id=10,
        stage_id=100,
        time_slot=TimeSlot(datetime(2027, 6, 18, 18, 0), datetime(2027, 6, 18, 19, 0)),
    )
    repo = InMemoryConcertRepository([concert])
    use_case = CancelConcertUseCase(repo)

    cancelled = use_case.execute(1)
    assert cancelled.is_cancelled
    assert repo.get_by_id(1).is_cancelled


def test_cancel_nonexistent_concert():
    repo = InMemoryConcertRepository()
    use_case = CancelConcertUseCase(repo)

    with pytest.raises(ConcertNotFoundError):
        use_case.execute(999)


def test_get_festival_schedule():
    c2 = Concert(
        id=2, festival_id=1, artist_id=20, stage_id=100,
        time_slot=TimeSlot(datetime(2027, 6, 18, 20, 0), datetime(2027, 6, 18, 21, 0)),
    )
    c1 = Concert(
        id=1, festival_id=1, artist_id=10, stage_id=100,
        time_slot=TimeSlot(datetime(2027, 6, 18, 18, 0), datetime(2027, 6, 18, 19, 0)),
    )
    repo = InMemoryConcertRepository([c2, c1])
    use_case = GetFestivalScheduleUseCase(repo)

    schedule = use_case.execute(festival_id=1)
    # Vérification du tri chronologique
    assert len(schedule) == 2
    assert schedule[0].id == 1
    assert schedule[1].id == 2
