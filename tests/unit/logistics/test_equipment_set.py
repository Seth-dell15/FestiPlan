import pytest

from app.domain.value_objects.equipment_set import EquipmentSet


def test_from_csv_ignores_blanks_and_spaces():
    assert EquipmentSet.from_csv(" large_rigging, ,special_lighting,") == EquipmentSet.of(
        ["large_rigging", "special_lighting"]
    )


def test_from_csv_accepts_empty_or_none():
    assert len(EquipmentSet.from_csv("")) == 0
    assert len(EquipmentSet.from_csv(None)) == 0


def test_csv_round_trip_is_stable():
    equipment = EquipmentSet.of(["special_lighting", "large_rigging"])
    assert equipment.to_csv() == "large_rigging,special_lighting"
    assert EquipmentSet.from_csv(equipment.to_csv()) == equipment


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
