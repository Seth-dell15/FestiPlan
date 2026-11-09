from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.exceptions.logistics_exceptions import InvalidFestivalDatesError
from app.domain.value_objects.utc_datetime import to_naive_utc


@dataclass(frozen=True)
class FestivalPeriod:
    """Période d'un festival : la fin doit être strictement après le début."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "start", to_naive_utc(self.start))
        object.__setattr__(self, "end", to_naive_utc(self.end))
        if self.end <= self.start:
            raise InvalidFestivalDatesError("La date de fin doit être postérieure à la date de début")
