from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class StageScheduleInfo:
    """Informations d'une scène nécessaires à la programmation (R4, R5)."""
    id: int
    festival_id: int
    name: str
    available_equipment: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ArtistScheduleInfo:
    """Informations d'un artiste nécessaires à la programmation (R4, R5)."""
    id: int
    name: str
    required_equipment: frozenset[str] = field(default_factory=frozenset)


class ISchedulingCatalogPort(Protocol):
    """Port sortant : consultation des scènes et artistes par le pôle Planification.

    Volontairement en lecture seule et limité aux champs utiles aux règles de
    programmation, sur le même modèle que IFestivalQueryPort. Le pôle Planification
    ne dépend ainsi ni des entités ni des repositories du pôle Référentiel : après la
    fusion, un adaptateur peut s'appuyer sur les repositories Stage/Artist existants.
    """

    def get_stage_info(self, stage_id: int) -> StageScheduleInfo | None:
        ...

    def get_artist_info(self, artist_id: int) -> ArtistScheduleInfo | None:
        ...
