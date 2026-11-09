from app.application.ports.inbound import IScheduleConcertPort, ScheduleConcertCommand
from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.ports.repositories.artist_repository_port import IArtistRepository
from app.domain.ports.repositories.concert_query_port import IConcertQueryPort
from app.domain.ports.repositories.schedule_repository_port import IScheduleRepository
from app.domain.ports.repositories.stage_repository_port import IStageRepository
from app.domain.exceptions.scheduling_exceptions import (
    UnknownArtistError,
    UnknownFestivalError,
    UnknownStageError,
)


class ScheduleConcertUseCase(IScheduleConcertPort):
    """Cas d'usage : Programmer un concert.

    Le cas d'usage charge le planning, la scène et l'artiste (R4 : références existantes),
    puis délègue au planning, qui garantit R2 à R7 avant d'accepter le concert.
    Tous les ports sont obligatoires : aucune règle ne peut être sautée par oubli d'injection.
    """

    def __init__(
        self,
        schedule_repository: IScheduleRepository,
        concert_query: IConcertQueryPort,
        stage_repository: IStageRepository,
        artist_repository: IArtistRepository,
    ):
        self._schedules = schedule_repository
        self._concerts = concert_query
        self._stages = stage_repository
        self._artists = artist_repository

    def execute(self, command: ScheduleConcertCommand) -> Concert:
        # R1 : le créneau valide lui-même ses bornes
        time_slot = TimeSlot(start=command.start_time, end=command.end_time)

        # R4 : le festival, la scène et l'artiste doivent exister
        schedule = self._schedules.get_by_festival_id(command.festival_id)
        if schedule is None:
            raise UnknownFestivalError(command.festival_id)
        stage = self._stages.get_by_id(command.stage_id)
        if stage is None:
            raise UnknownStageError(command.stage_id)
        artist = self._artists.get_by_id(command.artist_id)
        if artist is None:
            raise UnknownArtistError(command.artist_id)

        # R3 s'applique aussi entre festivals : un artiste est global.
        bookings_elsewhere = [
            booking
            for booking in self._concerts.list_for_artist(artist.id)
            if booking.festival_id != schedule.festival_id
        ]

        # R2 à R7 : garanties par la racine de l'agrégat
        concert = schedule.add_concert(artist, stage, time_slot, bookings_elsewhere)
        self._schedules.save(schedule)
        return concert
