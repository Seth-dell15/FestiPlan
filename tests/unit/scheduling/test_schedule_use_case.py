from datetime import datetime
import pytest
from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
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
from app.adapters.secondary.repositories.in_memory_concert_query_adapter import InMemoryConcertQueryAdapter
from app.adapters.secondary.repositories.in_memory_artist_repository import InMemoryArtistRepository
from app.adapters.secondary.repositories.in_memory_stage_repository import InMemoryStageRepository
from app.domain.models.artist import Artist
from app.domain.models.stage import Stage
from tests.unit.scheduling.test_reschedule_use_case import make_schedules


def make_catalog() -> dict:
    # Scène 100 (festival 1) et artistes 10 et 20 sans besoin technique particulier
    return dict(
        stage_repository=InMemoryStageRepository([Stage(id=100, festival_id=1, name="Mainstage", capacity=1000)]),
        artist_repository=InMemoryArtistRepository(
            [Artist(id=10, name="Iron Vow", genre="Heavy"), Artist(id=20, name="Crimson Engine", genre="Thrash")]
        ),
    )


def test_schedule_concert_success():
    repo = InMemoryConcertQueryAdapter()
    use_case = ScheduleConcertUseCase(
        schedule_repository=make_schedules(repo),
        concert_query=repo,
        **make_catalog(),
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


def test_schedule_concert_conflict_raises_stage_occupied():
    existing = Concert(
        id=1,
        festival_id=1,
        artist_id=10,
        stage_id=100,
        time_slot=TimeSlot(datetime(2027, 6, 18, 18, 0), datetime(2027, 6, 18, 19, 0)),
    )
    repo = InMemoryConcertQueryAdapter([existing])
    use_case = ScheduleConcertUseCase(
        schedule_repository=make_schedules(repo),
        concert_query=repo,
        **make_catalog(),
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
    repo = InMemoryConcertQueryAdapter([concert])
    use_case = CancelConcertUseCase(make_schedules(repo))

    cancelled = use_case.execute(1)
    assert cancelled.is_cancelled
    assert repo.get_by_id(1).is_cancelled


def test_cancel_nonexistent_concert():
    repo = InMemoryConcertQueryAdapter()
    use_case = CancelConcertUseCase(make_schedules(repo))

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
    repo = InMemoryConcertQueryAdapter([c2, c1])
    use_case = GetFestivalScheduleUseCase(repo)

    schedule = use_case.execute(festival_id=1)
    # Vérification du tri chronologique
    assert len(schedule) == 2
    assert schedule[0].id == 1
    assert schedule[1].id == 2
