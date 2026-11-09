from typing import Protocol

from app.domain.models.schedule import Schedule


class IScheduleRepository(Protocol):
    """Port sortant : charge et enregistre le planning d'un festival, racine de l'agrégat des concerts."""

    def get_by_festival_id(self, festival_id: int) -> Schedule | None:
        """Planning du festival avec tous ses concerts, ou None si le festival n'existe pas."""
        ...

    def get_by_concert_id(self, concert_id: int) -> Schedule | None:
        """Planning qui contient ce concert, ou None si le concert n'existe pas."""
        ...

    def save(self, schedule: Schedule) -> None:
        """Enregistre les concerts du planning en une seule transaction et attribue un id aux nouveaux."""
        ...
