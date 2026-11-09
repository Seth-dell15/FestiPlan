from app.application.ports.inbound import IScheduleConcertPort, ScheduleConcertCommand
from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.services import scheduling_policy as policy
from app.domain.ports.repositories.artist_repository_port import IArtistRepository
from app.domain.ports.repositories.concert_repository_port import IConcertRepository
from app.domain.ports.repositories.festival_repository_port import IFestivalQueryPort
from app.domain.ports.repositories.stage_repository_port import IStageRepository
from app.domain.exceptions.scheduling_exceptions import (
    UnknownArtistError,
    UnknownFestivalError,
    UnknownStageError,
)


class ScheduleConcertUseCase(IScheduleConcertPort):
    """Cas d'usage : Programmer un concert.

    Vérifie, dans cet ordre : R1 (créneau), R4 (festival, scène et artiste existants,
    scène du bon festival), R7 (planning non publié), R6 (dates du festival),
    R5 (équipements) puis R2/R3 (conflits), avant d'enregistrer le concert.
    Tous les ports sont obligatoires : aucune règle ne peut être sautée par oubli d'injection.
    """

    def __init__(
        self,
        concert_repository: IConcertRepository,
        festival_query_port: IFestivalQueryPort,
        stage_repository: IStageRepository,
        artist_repository: IArtistRepository,
    ):
        self._concert_repo = concert_repository
        self._festival_port = festival_query_port
        self._stages = stage_repository
        self._artists = artist_repository

    def execute(self, command: ScheduleConcertCommand) -> Concert:
        # R1 : le créneau valide lui-même ses bornes
        time_slot = TimeSlot(start=command.start_time, end=command.end_time)

        # R4 : le festival doit exister
        festival = self._festival_port.get_schedule_info(command.festival_id)
        if festival is None:
            raise UnknownFestivalError(command.festival_id)

        # R7 puis R6
        policy.ensure_festival_is_modifiable(festival)
        policy.ensure_within_festival(time_slot, festival)

        # R4 : la scène et l'artiste doivent exister ; R4/R5 : scène du festival, équipements
        stage = self._stages.get_by_id(command.stage_id)
        if stage is None:
            raise UnknownStageError(command.stage_id)
        artist = self._artists.get_by_id(command.artist_id)
        if artist is None:
            raise UnknownArtistError(command.artist_id)
        policy.ensure_stage_can_host(command.festival_id, stage, artist)

        # R2 et R3 : R3 s'applique aussi entre festivals, car un artiste est global.
        new_concert = Concert(
            festival_id=command.festival_id,
            artist_id=command.artist_id,
            stage_id=command.stage_id,
            time_slot=time_slot,
        )
        policy.ensure_no_conflict(
            new_concert,
            [
                *self._concert_repo.list_for_festival(festival_id=command.festival_id, include_cancelled=False),
                *self._concert_repo.list_for_artist(command.artist_id),
            ],
        )

        return self._concert_repo.save(new_concert)
