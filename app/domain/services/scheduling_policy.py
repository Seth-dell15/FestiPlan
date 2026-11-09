"""Politique de programmation : point unique où sont regroupées les règles du planning.

Les cas d'utilisation (programmer, déplacer, annuler, publier) appellent ces fonctions au lieu de
réécrire chacun leurs propres vérifications : une règle corrigée ici l'est partout.
Aucune dépendance à FastAPI ni à SQLAlchemy : testable sans base de données.
"""
from collections.abc import Iterable, Mapping, Sequence

from app.domain.models.artist import Artist
from app.domain.models.concert import Concert
from app.domain.models.festival import Festival
from app.domain.models.stage import Stage
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.ports.repositories.festival_repository_port import FestivalScheduleInfo
from app.domain.exceptions.logistics_exceptions import EquipmentMismatchError
from app.domain.exceptions.operation_exceptions import CannotPublishInvalidScheduleError
from app.domain.exceptions.scheduling_exceptions import (
    ArtistAlreadyBookedError,
    CannotModifyPublishedFestivalError,
    ConcertOutsideFestivalError,
    StageNotInFestivalError,
    StageOccupiedError,
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


def ensure_stage_can_host(festival_id: int, stage: Stage, artist: Artist) -> None:
    """R4 (scène du bon festival) et R5 (équipements requis, garantis par Stage)."""
    if not stage.belongs_to(festival_id):
        raise StageNotInFestivalError(stage.id, festival_id)
    stage.ensure_can_host(artist)


def ensure_no_conflict(candidate: Concert, others: Iterable[Concert]) -> None:
    """R2 (scène) et R3 (artiste) : aucun chevauchement avec les autres concerts actifs."""
    for other in others:
        candidate.check_conflict_with(other)


def ensure_publishable(
    festival: Festival,
    concerts: Sequence[Concert],
    stages: Mapping[int, Stage | None],
    artists: Mapping[int, Artist | None],
    bookings_elsewhere: Iterable[Concert] = (),
) -> None:
    """R8 : le planning existe et chaque concert respecte R2 à R6, y compris R3 entre festivals."""
    if not concerts:
        raise CannotPublishInvalidScheduleError("Impossible de publier un planning sans concert programmé.")

    bookings_elsewhere = tuple(bookings_elsewhere)
    for index, concert in enumerate(concerts):
        if not concert.time_slot.is_within(festival.period.start, festival.period.end):
            raise CannotPublishInvalidScheduleError(
                f"Impossible de publier le planning : le concert #{concert.id} déborde des dates du festival (R6)."
            )
        _ensure_concert_fits_its_stage(festival, concert, stages.get(concert.stage_id), artists.get(concert.artist_id))
        _ensure_no_publication_conflict(concert, (*concerts[index + 1:], *bookings_elsewhere))


def _ensure_concert_fits_its_stage(
    festival: Festival, concert: Concert, stage: Stage | None, artist: Artist | None
) -> None:
    if stage is None or artist is None:
        raise CannotPublishInvalidScheduleError(
            f"Impossible de publier le planning : le concert #{concert.id} référence une scène ou un artiste inconnu (R4)."
        )
    try:
        ensure_stage_can_host(festival.id, stage, artist)
    except (StageNotInFestivalError, EquipmentMismatchError) as exc:
        raise CannotPublishInvalidScheduleError(
            f"Impossible de publier le planning : concert #{concert.id} invalide ({exc}) (R4/R5)."
        ) from exc


def _ensure_no_publication_conflict(concert: Concert, others: Iterable[Concert]) -> None:
    try:
        ensure_no_conflict(concert, others)
    except (StageOccupiedError, ArtistAlreadyBookedError) as conflict:
        raise CannotPublishInvalidScheduleError(
            f"Impossible de publier le planning : conflit de programmation détecté ({conflict}) (R8)."
        ) from conflict
