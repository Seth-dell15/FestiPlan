from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace

from app.domain.events.concert_events import ConcertRescheduledEvent
from app.domain.exceptions.logistics_exceptions import EquipmentMismatchError
from app.domain.exceptions.operation_exceptions import CannotPublishInvalidScheduleError
from app.domain.exceptions.scheduling_exceptions import (
    ArtistAlreadyBookedError,
    CannotModifyPublishedFestivalError,
    ConcertAlreadyCancelledError,
    ConcertNotFoundError,
    ConcertOutsideFestivalError,
    StageNotInFestivalError,
    StageOccupiedError,
)
from app.domain.models.artist import Artist
from app.domain.models.concert import Concert
from app.domain.models.stage import Stage
from app.domain.value_objects.festival_period import FestivalPeriod
from app.domain.value_objects.time_slot import TimeSlot


@dataclass(eq=False)
class Schedule:
    """Planning d'un festival : racine d'agrégat, seul point d'entrée pour modifier ses concerts.

    Garantit R2 à R7 à chaque modification et sait dire s'il est publiable (R8). La période et
    l'état de publication sont ceux du festival, lus au chargement : R6 et R7 en ont besoin.
    """

    festival_id: int
    period: FestivalPeriod
    is_published: bool = False
    concerts: list[Concert] = field(default_factory=list)

    @property
    def active_concerts(self) -> list[Concert]:
        """Concerts non annulés, dans l'ordre chronologique."""
        return sorted((c for c in self.concerts if not c.is_cancelled), key=lambda c: c.time_slot.start)

    def get_concert(self, concert_id: int) -> Concert:
        for concert in self.concerts:
            if concert.id == concert_id:
                return concert
        raise ConcertNotFoundError(concert_id)

    def add_concert(
        self,
        artist: Artist,
        stage: Stage,
        time_slot: TimeSlot,
        bookings_elsewhere: Iterable[Concert] = (),
    ) -> Concert:
        """Programme un concert. `bookings_elsewhere` : concerts de l'artiste dans d'autres festivals (R3)."""
        self._ensure_modifiable()
        self._ensure_within_period(time_slot)
        self._ensure_stage_can_host(stage, artist)
        concert = Concert(
            festival_id=self.festival_id,
            artist_id=artist.id,
            stage_id=stage.id,
            time_slot=time_slot,
        )
        self._ensure_no_conflict(concert, bookings_elsewhere)
        self.concerts.append(concert)
        return concert

    def reschedule_concert(
        self,
        concert_id: int,
        new_time_slot: TimeSlot,
        bookings_elsewhere: Iterable[Concert] = (),
    ) -> ConcertRescheduledEvent:
        """Déplace un concert et renvoie l'événement qui décrit le fait accompli."""
        concert = self.get_concert(concert_id)
        if concert.is_cancelled:
            raise ConcertAlreadyCancelledError("Impossible de déplacer un concert annulé")
        self._ensure_modifiable()
        self._ensure_within_period(new_time_slot)
        # Les conflits sont vérifiés sur une copie : le concert réel n'est modifié qu'une fois tout validé.
        self._ensure_no_conflict(replace(concert, time_slot=new_time_slot), bookings_elsewhere)
        return concert.reschedule(new_time_slot)

    def cancel_concert(self, concert_id: int) -> Concert:
        concert = self.get_concert(concert_id)
        self._ensure_modifiable()
        concert.cancel()
        return concert

    def ensure_publishable(
        self,
        stages: Mapping[int, Stage | None],
        artists: Mapping[int, Artist | None],
        bookings_elsewhere: Iterable[Concert] = (),
    ) -> None:
        """R8 : le planning existe et chaque concert respecte R2 à R6, y compris R3 entre festivals."""
        concerts = self.active_concerts
        if not concerts:
            raise CannotPublishInvalidScheduleError("Impossible de publier un planning sans concert programmé.")

        bookings_elsewhere = tuple(bookings_elsewhere)
        for index, concert in enumerate(concerts):
            if not concert.time_slot.is_within(self.period.start, self.period.end):
                raise CannotPublishInvalidScheduleError(
                    f"Impossible de publier le planning : le concert #{concert.id} déborde des dates du festival (R6)."
                )
            self._ensure_concert_fits_its_stage(concert, stages.get(concert.stage_id), artists.get(concert.artist_id))
            try:
                for other in (*concerts[index + 1:], *bookings_elsewhere):
                    concert.check_conflict_with(other)
            except (StageOccupiedError, ArtistAlreadyBookedError) as conflict:
                raise CannotPublishInvalidScheduleError(
                    f"Impossible de publier le planning : conflit de programmation détecté ({conflict}) (R8)."
                ) from conflict

    def _ensure_concert_fits_its_stage(self, concert: Concert, stage: Stage | None, artist: Artist | None) -> None:
        if stage is None or artist is None:
            raise CannotPublishInvalidScheduleError(
                f"Impossible de publier le planning : le concert #{concert.id} "
                "référence une scène ou un artiste inconnu (R4)."
            )
        try:
            self._ensure_stage_can_host(stage, artist)
        except (StageNotInFestivalError, EquipmentMismatchError) as exc:
            raise CannotPublishInvalidScheduleError(
                f"Impossible de publier le planning : concert #{concert.id} invalide ({exc}) (R4/R5)."
            ) from exc

    def _ensure_modifiable(self) -> None:
        """R7 : un planning publié ne peut pas être modifié par une opération ordinaire."""
        if self.is_published:
            raise CannotModifyPublishedFestivalError(
                f"Le festival #{self.festival_id} a déjà été publié. "
                "Les modifications ordinaires du planning sont verrouillées."
            )

    def _ensure_within_period(self, time_slot: TimeSlot) -> None:
        """R6 : le concert se déroule entièrement pendant le festival."""
        if not time_slot.is_within(self.period.start, self.period.end):
            raise ConcertOutsideFestivalError(
                f"Le créneau ({time_slot.start} - {time_slot.end}) ne s'inscrit pas "
                f"dans les dates du festival ({self.period.start} - {self.period.end})"
            )

    def _ensure_stage_can_host(self, stage: Stage, artist: Artist) -> None:
        """R4 (scène du festival) et R5 (équipements requis)."""
        if not stage.belongs_to(self.festival_id):
            raise StageNotInFestivalError(stage.id, self.festival_id)
        stage.ensure_can_host(artist)

    def _ensure_no_conflict(self, candidate: Concert, bookings_elsewhere: Iterable[Concert]) -> None:
        """R2 (scène) et R3 (artiste, y compris dans un autre festival)."""
        for other in (*self.concerts, *bookings_elsewhere):
            candidate.check_conflict_with(other)
