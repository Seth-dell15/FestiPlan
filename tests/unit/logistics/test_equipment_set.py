import pytest

from app.domain.value_objects.equipment_set import EquipmentSet


def test_covers_when_all_required_items_are_available():
    stage = EquipmentSet.of(["large_rigging", "special_lighting", "pyrotechnics"])
    assert stage.covers(EquipmentSet.of(["large_rigging", "special_lighting"]))
    assert stage.covers(EquipmentSet())


def test_does_not_cover_when_an_item_is_missing():
    stage = EquipmentSet.of(["special_lighting"])
    required = EquipmentSet.of(["large_rigging", "special_lighting"])
    assert not stage.covers(required)
    assert stage.missing(required) == EquipmentSet.of(["large_rigging"])


def test_is_immutable():
    equipment = EquipmentSet.of(["special_lighting"])
    with pytest.raises(AttributeError):
        equipment.items = frozenset()
