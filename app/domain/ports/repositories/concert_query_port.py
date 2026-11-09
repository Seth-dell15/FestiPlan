from typing import Protocol

from app.domain.models.concert import Concert


class IConcertQueryPort(Protocol):
    """Port sortant de consultation des concerts.

    Lecture seule : toute modification passe par le planning (IScheduleRepository).
    """

    def get_by_id(self, concert_id: int) -> Concert | None:
        """Récupère un concert par son identifiant unique."""
        ...

    def list_for_festival(self, festival_id: int, include_cancelled: bool = False) -> list[Concert]:
        """Récupère tous les concerts d'un festival, ordonnés par heure de début."""
        ...

    def list_for_artist(self, artist_id: int) -> list[Concert]:
        """Récupère les concerts actifs d'un artiste, tous festivals confondus (R3)."""
        ...
