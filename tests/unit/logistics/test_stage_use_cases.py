from datetime import datetime

import pytest

from app.adapters.secondary.repositories.in_memory_festival_repository import InMemoryFestivalRepository
from app.adapters.secondary.repositories.in_memory_stage_repository import InMemoryStageRepository
from app.application.use_cases.logistics.create_stage import CreateStageCommand, CreateStageUseCase
from app.application.use_cases.logistics.list_stages import ListStagesUseCase
from app.domain.exceptions.logistics_exceptions import FestivalNotFoundError, InvalidCapacityError
from app.domain.models.festival import Festival
from app.domain.value_objects.equipment_set import EquipmentSet
from app.domain.value_objects.festival_period import FestivalPeriod


def make_festival():
    return Festival(
        name="Hellforge Open Air",
        location="Clisson-sur-Rivière",
        period=FestivalPeriod(start=datetime(2027, 6, 18, 10, 0), end=datetime(2027, 6, 20, 23, 59)),
    )


@pytest.fixture
def festivals():
    return InMemoryFestivalRepository([make_festival(), make_festival()])


@pytest.fixture
def stages():
    return InMemoryStageRepository()


def command(festival_id=1, capacity=8000, equipment=("special_lighting",)):
    return CreateStageCommand(festival_id=festival_id, name="Valley", capacity=capacity, available_equipment=equipment)


def test_create_stage_in_existing_festival(stages, festivals):
    stage = CreateStageUseCase(stages, festivals).execute(command())

    assert stage.id is not None
    assert stage.belongs_to(1)
    assert stage.available_equipment == EquipmentSet.of(["special_lighting"])
    assert stages.get(stage.id) is stage


def test_create_stage_in_unknown_festival_saves_nothing(stages, festivals):
    use_case = CreateStageUseCase(stages, festivals)
    unknown_festival = command(festival_id=99)

    with pytest.raises(FestivalNotFoundError):
        use_case.execute(unknown_festival)

    assert stages.list_for_festival(99) == []


def test_create_stage_with_zero_capacity_is_refused_without_http(stages, festivals):
    use_case = CreateStageUseCase(stages, festivals)
    zero_capacity = command(capacity=0)

    with pytest.raises(InvalidCapacityError):
        use_case.execute(zero_capacity)

    assert stages.list_for_festival(1) == []


def test_list_stages_returns_only_those_of_the_festival(stages, festivals):
    create = CreateStageUseCase(stages, festivals)
    first = create.execute(command(festival_id=1))
    create.execute(command(festival_id=2))
    third = create.execute(command(festival_id=1))

    assert ListStagesUseCase(stages).execute(1) == [first, third]
