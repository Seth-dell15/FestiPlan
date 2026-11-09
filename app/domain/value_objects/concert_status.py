from enum import Enum


class ConcertStatus(str, Enum):
    # Valeurs identiques aux chaînes déjà stockées en base.
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
