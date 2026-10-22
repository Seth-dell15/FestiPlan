from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.value_objects.equipment_set import EquipmentSet


@dataclass(eq=False, kw_only=True)
class Artist:
    name: str
    genre: str
    required_equipment: EquipmentSet = field(default_factory=EquipmentSet)
    id: int | None = None
