from dataclasses import dataclass
from datetime import datetime

from app.domain.models.festival import Festival
from app.domain.ports.repositories.festival_repository_port import FestivalRepositoryPort
from app.domain.value_objects.festival_period import FestivalPeriod


@dataclass(frozen=True)
class CreateFestivalCommand:
    name: str
    location: str
    start_date: datetime
    end_date: datetime


class CreateFestivalUseCase:
    def __init__(self, festival_repository: FestivalRepositoryPort):
        self._festivals = festival_repository

    def execute(self, command: CreateFestivalCommand) -> Festival:
        # FestivalPeriod refuse des dates incohérentes avant tout enregistrement.
        festival = Festival(
            name=command.name,
            location=command.location,
            period=FestivalPeriod(start=command.start_date, end=command.end_date),
        )
        return self._festivals.save(festival)
