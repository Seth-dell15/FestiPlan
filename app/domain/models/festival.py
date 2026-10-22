from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.festival_status import FestivalStatus


# eq=False : une entité se distingue par son identité, pas par la valeur de ses champs.
@dataclass(eq=False, kw_only=True)
class Festival:
    name: str
    location: str
    period: FestivalPeriod
    status: FestivalStatus = FestivalStatus.PREPARATION
    id: int | None = None

    @property
    def is_published(self) -> bool:
        return self.status is FestivalStatus.PUBLISHED
