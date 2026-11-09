from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class EquipmentSet:
    """Ensemble immuable d'équipements (besoins d'un artiste ou dotation d'une scène)."""

    items: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        normalized = frozenset(item.strip() for item in self.items if item and item.strip())
        object.__setattr__(self, "items", normalized)

    @classmethod
    def of(cls, items: Iterable[str]) -> EquipmentSet:
        return cls(frozenset(items))

    @classmethod
    def from_csv(cls, raw: str | None) -> EquipmentSet:
        # Format de stockage hérité de la base : "a,b,c".
        return cls.of((raw or "").split(","))

    def to_csv(self) -> str:
        return ",".join(sorted(self.items))

    def covers(self, required: EquipmentSet) -> bool:
        return required.items <= self.items

    def missing(self, required: EquipmentSet) -> EquipmentSet:
        return EquipmentSet(required.items - self.items)

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self.items))

    def __len__(self) -> int:
        return len(self.items)
