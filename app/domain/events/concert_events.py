from dataclasses import dataclass
from datetime import datetime
from app.domain.value_objects.time_slot import TimeSlot


@dataclass(frozen=True)
class ConcertRescheduledEvent:
    """Événement de domaine émis lorsqu'un concert a été déplacé avec succès."""
    concert_id: int
    festival_id: int
    previous_time_slot: TimeSlot
    new_time_slot: TimeSlot
    occurred_at: datetime
