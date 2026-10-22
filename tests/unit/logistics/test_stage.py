import pytest

from app.domain.exceptions.logistics_exceptions import EquipmentMismatchError, InvalidCapacityError
from app.domain.models.artist import Artist
from app.domain.models.stage import Stage
from app.domain.value_objects.equipment_set import EquipmentSet


def make_stage(capacity=8000, available=("special_lighting",)):
    return Stage(festival_id=1, name="Valley", capacity=capacity, available_equipment=EquipmentSet.of(available))


def make_artist(required=()):
    return Artist(name="Iron Vow", genre="Heavy metal", required_equipment=EquipmentSet.of(required))


@pytest.mark.parametrize("capacity", [0, -1])
def test_capacity_must_be_strictly_positive(capacity):
    with pytest.raises(InvalidCapacityError):
        make_stage(capacity=capacity)


def test_belongs_to_its_festival_only():
    stage = make_stage()
    assert stage.belongs_to(1)
    assert not stage.belongs_to(2)


def test_can_host_artist_without_requirements():
    assert make_stage(available=()).can_host(make_artist())


def test_can_host_artist_when_equipment_is_available():
    stage = make_stage(available=("large_rigging", "special_lighting"))
    assert stage.can_host(make_artist(required=("large_rigging",)))


def test_cannot_host_artist_when_equipment_is_missing():
    stage = make_stage(available=("special_lighting",))
    artist = make_artist(required=("large_rigging", "special_lighting"))
    assert not stage.can_host(artist)
    with pytest.raises(EquipmentMismatchError, match="large_rigging"):
        stage.ensure_can_host(artist)


def test_ensure_can_host_passes_when_equipment_is_available():
    make_stage().ensure_can_host(make_artist(required=("special_lighting",)))
