from dataclasses import dataclass
from datetime import datetime, timedelta
from app.domain.exceptions.scheduling_exceptions import InvalidTimeSlotError


@dataclass(frozen=True)
class TimeSlot:
    """Objet-Valeur immuable représentant un créneau horaire.
    
    Garantit l'invariant R1 : l'heure de fin doit être strictement postérieure à l'heure de début.
    Fournit les méthodes métier pures pour le calcul d'intersection et d'inclusion.
    """
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise InvalidTimeSlotError(
                f"Créneau invalide : fin ({self.end.isoformat()}) doit être > début ({self.start.isoformat()})"
            )

    @property
    def duration(self) -> timedelta:
        """Retourne la durée du créneau."""
        return self.end - self.start

    def overlaps(self, other: "TimeSlot") -> bool:
        """Règle métier : détermine si deux créneaux se chevauchent.
        
        Deux créneaux [A_start, A_end[ et [B_start, B_end[ se chevauchent si et seulement si
        A_start < B_end et B_start < A_end.
        Deux concerts contigus (A_end == B_start) ne se chevauchent PAS.
        """
        return self.start < other.end and other.start < self.end

    def is_within(self, period_start: datetime, period_end: datetime) -> bool:
        """Règle métier R6 : vérifie si le créneau est entièrement compris dans une période."""
        return self.start >= period_start and self.end <= period_end
