from dataclasses import dataclass
from datetime import datetime
from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.ports.repositories.concert_repository_port import IConcertRepository
from app.domain.ports.repositories.festival_repository_port import IFestivalQueryPort
from app.domain.exceptions.scheduling_exceptions import (
    ConcertOutsideFestivalError,
    CannotModifyPublishedFestivalError,
)


@dataclass(frozen=True)
class ScheduleConcertCommand:
    """Commande pour programmer un nouveau concert."""
    festival_id: int
    artist_id: int
    stage_id: int
    start_time: datetime
    end_time: datetime


class ScheduleConcertUseCase:
    """Cas d'usage : Programmer un concert."""

    def __init__(
        self,
        concert_repository: IConcertRepository,
        festival_query_port: IFestivalQueryPort | None = None,
    ):
        self._concert_repo = concert_repository
        self._festival_port = festival_query_port

    def execute(self, command: ScheduleConcertCommand) -> Concert:
        # 1. R1 : vérification du créneau horaire
        time_slot = TimeSlot(start=command.start_time, end=command.end_time)

        # 2. R6 & R7 : vérification par rapport au festival
        if self._festival_port is not None:
            festival_info = self._festival_port.get_schedule_info(command.festival_id)
            if festival_info is not None:
                if festival_info.is_published:
                    raise CannotModifyPublishedFestivalError(
                        f"Impossible de programmer un concert sur le festival #{command.festival_id} déjà publié."
                    )
                if not time_slot.is_within(festival_info.start_date, festival_info.end_date):
                    raise ConcertOutsideFestivalError(
                        f"Le créneau ({time_slot.start} - {time_slot.end}) ne s'inscrit pas "
                        f"dans les dates du festival ({festival_info.start_date} - {festival_info.end_date})"
                    )

        # 3. Création du concert candidat
        new_concert = Concert(
            festival_id=command.festival_id,
            artist_id=command.artist_id,
            stage_id=command.stage_id,
            time_slot=time_slot,
        )

        # 4. R2 & R3 : vérification des conflits avec les concerts existants
        existing = self._concert_repo.list_for_festival(
            festival_id=command.festival_id,
            include_cancelled=False,
        )
        for other in existing:
            new_concert.check_conflict_with(other)

        # 5. Persistance
        return self._concert_repo.save(new_concert)
