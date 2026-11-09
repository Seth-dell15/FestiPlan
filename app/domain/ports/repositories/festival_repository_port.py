from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.models.festival import Festival


class IFestivalRepository(Protocol):
    def get_by_id(self, festival_id: int) -> Festival | None: ...

    def list(self) -> list[Festival]: ...

    def save(self, festival: Festival) -> Festival:
        """Crée le festival s'il n'a pas d'id, le met à jour sinon. Renvoie le festival avec son id."""
        ...


@dataclass(frozen=True)
class FestivalScheduleInfo:
    """Informations légères sur le festival requises pour les règles de programmation (R6, R7)."""
    id: int
    name: str
    start_date: datetime
    end_date: datetime
    is_published: bool


class IFestivalQueryPort(Protocol):
    """Port sortant pour consulter les informations d'un festival requises par la planification."""

    def get_schedule_info(self, festival_id: int) -> FestivalScheduleInfo | None:
        """Récupère les dates et le statut de publication d'un festival."""
        ...


class IFestivalCommandPort(Protocol):
    """Port sortant pour modifier le statut du festival (ex: publication)."""

    def publish_festival(self, festival_id: int) -> FestivalScheduleInfo | None:
        """Passe le statut du festival à 'published' et renvoie les infos mises à jour."""
        ...
