from enum import Enum


class FestivalStatus(str, Enum):
    # Valeurs identiques aux chaînes déjà stockées en base.
    PREPARATION = "preparation"
    PUBLISHED = "published"
