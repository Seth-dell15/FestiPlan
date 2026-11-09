"""Ports entrants : ce que le cœur applicatif permet de faire depuis l'extérieur.

Limités aux commandes métier principales ; les lectures simples n'ont pas besoin de ce contrat.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.models.concert import Concert
from app.domain.models.festival import Festival
from app.domain.models.incident import Incident


@dataclass(frozen=True)
class ScheduleConcertCommand:
    """Commande pour programmer un nouveau concert."""
    festival_id: int
    artist_id: int
    stage_id: int
    start_time: datetime
    end_time: datetime


class IScheduleConcertPort(Protocol):
    def execute(self, command: ScheduleConcertCommand) -> Concert: ...


@dataclass(frozen=True)
class RescheduleConcertCommand:
    """Commande applicative pour déplacer un concert."""
    concert_id: int
    new_start: datetime
    new_end: datetime


@dataclass(frozen=True)
class RescheduleConcertResult:
    """Distingue la réussite de l'opération métier du statut de la notification."""
    concert: Concert
    notification_sent: bool
    notification_error: str | None = None


class IRescheduleConcertPort(Protocol):
    def execute(self, command: RescheduleConcertCommand) -> RescheduleConcertResult: ...


@dataclass(frozen=True)
class PublishFestivalResult:
    festival: Festival
    notification_sent: bool


class IPublishFestivalPort(Protocol):
    def execute(self, festival_id: int) -> PublishFestivalResult: ...


@dataclass(frozen=True)
class DeclareIncidentCommand:
    concert_id: int
    description: str
    occurred_at: datetime | None = None


class IDeclareIncidentPort(Protocol):
    def execute(self, command: DeclareIncidentCommand) -> Incident: ...
