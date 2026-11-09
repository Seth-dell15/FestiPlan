from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IncidentReportedEvent:
    """Événement déclenché lors du signalement d'un incident."""
    incident_id: int
    concert_id: int
    description: str
    occurred_at: datetime


@dataclass(frozen=True)
class IncidentResolvedEvent:
    """Événement déclenché lors de la résolution d'un incident."""
    incident_id: int
    resolved_at: datetime


@dataclass(frozen=True)
class FestivalPublishedEvent:
    """Événement déclenché lors de la publication officielle d'un festival."""
    festival_id: int
    festival_name: str
    published_at: datetime
