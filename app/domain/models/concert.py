from dataclasses import dataclass
from datetime import datetime, timezone
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.events.concert_events import ConcertRescheduledEvent
from app.domain.exceptions.scheduling_exceptions import (
    StageOccupiedError,
    ArtistAlreadyBookedError,
)


@dataclass
class Concert:
    """Entité pure du domaine représentant un concert.
    
    Possède une identité propre, un cycle de vie (programmé / annulé),
    et encapsule ses règles de mutation (reschedule, cancel).
    """
    festival_id: int
    artist_id: int
    stage_id: int
    time_slot: TimeSlot
    id: int | None = None
    status: str = "scheduled"

    @property
    def is_cancelled(self) -> bool:
        return self.status == "cancelled"

    def reschedule(self, new_time_slot: TimeSlot) -> ConcertRescheduledEvent:
        """Déplace le concert sur un nouveau créneau et produit un événement de domaine."""
        if self.is_cancelled:
            raise ValueError("Impossible de déplacer un concert annulé")
        
        previous_slot = self.time_slot
        self.time_slot = new_time_slot

        return ConcertRescheduledEvent(
            concert_id=self.id or 0,
            festival_id=self.festival_id,
            previous_time_slot=previous_slot,
            new_time_slot=new_time_slot,
            occurred_at=datetime.now(timezone.utc),
        )

    def cancel(self) -> None:
        """Annule le concert."""
        self.status = "cancelled"

    def check_conflict_with(self, other: "Concert") -> None:
        """Règles R2 et R3 : vérifie l'absence de conflit avec un autre concert.
        
        Lève StageOccupiedError ou ArtistAlreadyBookedError si chevauchement détecté.
        """
        # Un concert annulé ne génère aucun conflit
        if self.is_cancelled or other.is_cancelled:
            return

        # Même concert en base (même ID) : pas de conflit avec soi-même
        if self.id is not None and other.id is not None and self.id == other.id:
            return

        # S'il n'y a pas de chevauchement temporel, pas de conflit
        if not self.time_slot.overlaps(other.time_slot):
            return

        # Règle R2 : Deux concerts sur la même scène ne peuvent pas se chevaucher
        if self.stage_id == other.stage_id:
            raise StageOccupiedError(
                f"Conflit de scène (scène #{self.stage_id}) : "
                f"le créneau {self.time_slot.start} - {self.time_slot.end} chevauche un autre concert"
            )

        # Règle R3 : Un même artiste ne peut pas jouer sur deux scènes en même temps
        if self.artist_id == other.artist_id:
            raise ArtistAlreadyBookedError(
                f"Conflit d'artiste (artiste #{self.artist_id}) : "
                f"l'artiste est déjà programmé sur un créneau chevauchant"
            )
