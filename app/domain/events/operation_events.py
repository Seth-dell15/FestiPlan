from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FestivalPublishedEvent:
    """Événement émis lorsque le planning d'un festival a été publié."""
    festival_id: int
    festival_name: str
    published_at: datetime
