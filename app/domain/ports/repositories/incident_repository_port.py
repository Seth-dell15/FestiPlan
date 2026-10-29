from typing import Protocol
from app.domain.models.incident import Incident


class IIncidentRepository(Protocol):
    """Port sortant définissant le contrat de persistance pour les incidents."""

    def save(self, incident: Incident) -> Incident:
        """Enregistre ou met à jour un incident dans le système de persistance."""
        ...

    def get_by_id(self, incident_id: int) -> Incident | None:
        """Récupère un incident par son identifiant unique."""
        ...

    def list_all(self) -> list[Incident]:
        """Récupère la liste de tous les incidents ordonnés par date antéchronologique."""
        ...

    def list_by_concert(self, concert_id: int) -> list[Incident]:
        """Récupère la liste des incidents rattachés à un concert donné."""
        ...
