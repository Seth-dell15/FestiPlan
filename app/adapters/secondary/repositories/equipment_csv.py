"""Format de stockage des équipements : du texte "a,b,c" dans une seule colonne."""
from app.domain.value_objects.equipment_set import EquipmentSet


def equipment_from_csv(raw: str | None) -> EquipmentSet:
    return EquipmentSet.of((raw or "").split(","))


def equipment_to_csv(equipment: EquipmentSet) -> str:
    return ",".join(equipment)
