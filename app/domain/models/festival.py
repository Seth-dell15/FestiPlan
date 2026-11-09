from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.events.operation_events import FestivalPublishedEvent
from app.domain.exceptions.operation_exceptions import FestivalAlreadyPublishedError
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

    def publish(self) -> FestivalPublishedEvent:
        if self.is_published:
            raise FestivalAlreadyPublishedError(f"Le festival '{self.name}' est déjà publié.")
        self.status = FestivalStatus.PUBLISHED
        return FestivalPublishedEvent(
            festival_id=self.id or 0,
            festival_name=self.name,
            published_at=datetime.now(timezone.utc),
        )
