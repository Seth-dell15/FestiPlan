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
