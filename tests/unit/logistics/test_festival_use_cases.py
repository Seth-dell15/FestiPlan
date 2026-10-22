from datetime import datetime

import pytest

from app.adapters.secondary.repositories.in_memory_festival_repository import InMemoryFestivalRepository
from app.application.use_cases.logistics.create_festival import CreateFestivalCommand, CreateFestivalUseCase
from app.application.use_cases.logistics.get_festival import GetFestivalUseCase
from app.application.use_cases.logistics.list_festivals import ListFestivalsUseCase
from app.domain.exceptions.logistics_exceptions import FestivalNotFoundError, InvalidFestivalDatesError
from app.domain.value_objects.festival_status import FestivalStatus

START = datetime(2027, 6, 18, 10, 0)
END = datetime(2027, 6, 20, 23, 59)


def command(name="Hellforge Open Air", start=START, end=END):
    return CreateFestivalCommand(name=name, location="Clisson-sur-Rivière", start_date=start, end_date=end)


def test_create_festival_saves_it_in_preparation():
    repository = InMemoryFestivalRepository()

    festival = CreateFestivalUseCase(repository).execute(command())

    assert festival.id is not None
    assert festival.status is FestivalStatus.PREPARATION
    assert repository.get(festival.id) is festival


def test_create_festival_with_end_before_start_saves_nothing():
    repository = InMemoryFestivalRepository()
    use_case = CreateFestivalUseCase(repository)
    invalid = command(start=END, end=START)

    with pytest.raises(InvalidFestivalDatesError):
        use_case.execute(invalid)

    assert repository.list() == []


def test_list_festivals_returns_them_in_creation_order():
    repository = InMemoryFestivalRepository()
    create = CreateFestivalUseCase(repository)
    first = create.execute(command(name="Premier"))
    second = create.execute(command(name="Second"))

    assert ListFestivalsUseCase(repository).execute() == [first, second]


def test_get_festival_returns_the_saved_festival():
    repository = InMemoryFestivalRepository()
    festival = CreateFestivalUseCase(repository).execute(command())

    assert GetFestivalUseCase(repository).execute(festival.id) is festival


def test_get_unknown_festival_raises_not_found():
    use_case = GetFestivalUseCase(InMemoryFestivalRepository())

    with pytest.raises(FestivalNotFoundError):
        use_case.execute(42)
