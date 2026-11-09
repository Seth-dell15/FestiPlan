from dataclasses import dataclass, field
from datetime import datetime, timezone
from app.domain.exceptions.operation_exceptions import (
    IncidentInvalidDescriptionError,
    IncidentAlreadyResolvedError,
)
from app.domain.events.operation_events import IncidentResolvedEvent


@dataclass
class Incident:
    """Entité pure du Domaine représentant un incident survenu lors d'un concert.
    
    Invariants garantis :
    - R10 : Rattaché à un concert (concert_id > 0) et description textuelle non vide.
    """
    concert_id: int
    description: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    resolved: bool = False
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.description or not self.description.strip():
            raise IncidentInvalidDescriptionError(
                "La description de l'incident ne peut pas être vide (Règle R10)."
            )
        if self.concert_id <= 0:
            raise IncidentInvalidDescriptionError(
                "Un incident doit obligatoirement être rattaché à un concert existant (Règle R10)."
            )
        self.description = self.description.strip()

    def resolve(self) -> IncidentResolvedEvent:
        """Résout l'incident et produit l'événement de domaine correspondant."""
        if self.resolved:
            raise IncidentAlreadyResolvedError(
                f"L'incident #{self.id or 'nouveau'} est déjà résolu."
            )
        self.resolved = True
        return IncidentResolvedEvent(
            incident_id=self.id or 0,
            resolved_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
