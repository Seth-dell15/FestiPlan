from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.exceptions.logistics_exceptions import EquipmentMismatchError, InvalidCapacityError
from app.domain.models.artist import Artist
from app.domain.value_objects.equipment_set import EquipmentSet


@dataclass(eq=False, kw_only=True)
class Stage:
    festival_id: int
    name: str
    capacity: int
    available_equipment: EquipmentSet = field(default_factory=EquipmentSet)
    id: int | None = None

    def __post_init__(self) -> None:
        # R9 : vérifié ici et pas seulement par Pydantic, pour valoir hors HTTP.
        if self.capacity <= 0:
            raise InvalidCapacityError("La capacité d'une scène doit être strictement positive")

    def belongs_to(self, festival_id: int) -> bool:
        return self.festival_id == festival_id

    def can_host(self, artist: Artist) -> bool:
        return self.available_equipment.covers(artist.required_equipment)

    def ensure_can_host(self, artist: Artist) -> None:
        missing = self.available_equipment.missing(artist.required_equipment)
        if missing:
            raise EquipmentMismatchError(
                f"La scène {self.name} ne dispose pas des équipements requis : {', '.join(missing)}"
            )
