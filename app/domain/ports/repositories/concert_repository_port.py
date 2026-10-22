from typing import Protocol
from app.domain.models.concert import Concert


class IConcertRepository(Protocol):
    """Port sortant pour la persistance et la consultation des concerts.
    
    Définit le contrat d'accès aux données sans dépendance technique (SQLAlchemy, etc.).
    """

    def get_by_id(self, concert_id: int) -> Concert | None:
        """Récupère un concert par son identifiant unique."""
        ...

    def list_for_festival(self, festival_id: int, include_cancelled: bool = False) -> list[Concert]:
        """Récupère tous les concerts d'un festival, ordonnés par heure de début."""
        ...

    def save(self, concert: Concert) -> Concert:
        """Sauvegarde (création ou mise à jour) un concert et retourne l'entité persistée."""
        ...

    def delete(self, concert_id: int) -> None:
        """Supprime un concert de la persistance."""
        ...
