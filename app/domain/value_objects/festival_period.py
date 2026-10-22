from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.exceptions.logistics_exceptions import InvalidFestivalDatesError


@dataclass(frozen=True)
class FestivalPeriod:
    """Période d'un festival : la fin doit être strictement après le début."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise InvalidFestivalDatesError("La date de fin doit être postérieure à la date de début")

    def contains(self, start: datetime, end: datetime) -> bool:
        # Prend deux datetime plutôt qu'un TimeSlot pour ne pas dépendre du pôle planification.
        return self.start <= start and end <= self.end
