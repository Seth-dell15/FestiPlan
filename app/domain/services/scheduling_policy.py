"""Politique de programmation : point unique où sont regroupées les règles du planning.

Les cas d'utilisation (programmer, déplacer, annuler) appellent ces fonctions au lieu de
réécrire chacun leurs propres vérifications : une règle corrigée ici l'est partout.
Aucune dépendance à FastAPI ni à SQLAlchemy : testable sans base de données.
"""
from collections.abc import Iterable

from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.ports.repositories.festival_repository_port import FestivalScheduleInfo
from app.domain.ports.repositories.scheduling_catalog_port import ArtistScheduleInfo, StageScheduleInfo
from app.domain.exceptions.scheduling_exceptions import (
    CannotModifyPublishedFestivalError,
    ConcertOutsideFestivalError,
    MissingStageEquipmentError,
    StageNotInFestivalError,
)


def ensure_festival_is_modifiable(festival: FestivalScheduleInfo) -> None:
    """R7 : un planning publié ne peut pas être modifié par une opération ordinaire."""
    if festival.is_published:
        raise CannotModifyPublishedFestivalError(
            f"Le festival #{festival.id} a déjà été publié. "
            "Les modifications ordinaires du planning sont verrouillées."
        )


def ensure_within_festival(slot: TimeSlot, festival: FestivalScheduleInfo) -> None:
    """R6 : le concert doit se dérouler entièrement pendant la période du festival."""
    if not slot.is_within(festival.start_date, festival.end_date):
        raise ConcertOutsideFestivalError(
            f"Le créneau ({slot.start} - {slot.end}) ne s'inscrit pas "
            f"dans les dates du festival ({festival.start_date} - {festival.end_date})"
        )


def ensure_stage_can_host(festival_id: int, stage: StageScheduleInfo, artist: ArtistScheduleInfo) -> None:
    """R4 (scène du bon festival) et R5 (équipements requis disponibles)."""
    if stage.festival_id != festival_id:
        raise StageNotInFestivalError(stage.id, festival_id)
    missing = artist.required_equipment - stage.available_equipment
    if missing:
        raise MissingStageEquipmentError(stage.name, frozenset(missing))


def ensure_no_conflict(candidate: Concert, others: Iterable[Concert]) -> None:
    """R2 (scène) et R3 (artiste) : aucun chevauchement avec les autres concerts actifs."""
    for other in others:
        candidate.check_conflict_with(other)
