import logging
from app.application.ports.inbound import (
    IRescheduleConcertPort,
    RescheduleConcertCommand,
    RescheduleConcertResult,
)
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.ports.repositories.concert_query_port import IConcertQueryPort
from app.domain.ports.repositories.schedule_repository_port import IScheduleRepository
from app.domain.ports.services.notification_sender_port import INotificationSenderPort
from app.domain.exceptions.scheduling_exceptions import ConcertNotFoundError

logger = logging.getLogger(__name__)


class RescheduleConcertUseCase(IRescheduleConcertPort):
    """Cas d'usage : Déplacer un concert.

    Corrige le Défaut 1 : le déplacement passe par le planning, qui applique les mêmes règles
    que la programmation (concert annulé refusé, R7, R6, R2 et R3). La scène et l'artiste ne
    changent pas, donc R4 et R5 restent satisfaites.
    Isole ensuite la notification (Défaut 2).
    """

    def __init__(
        self,
        schedule_repository: IScheduleRepository,
        concert_query: IConcertQueryPort,
        notification_sender: INotificationSenderPort,
    ):
        self._schedules = schedule_repository
        self._concerts = concert_query
        self._notification_sender = notification_sender

    def execute(self, command: RescheduleConcertCommand) -> RescheduleConcertResult:
        # 1. Création du nouveau créneau (vérifie R1)
        new_slot = TimeSlot(start=command.new_start, end=command.new_end)

        # 2. Chargement du planning qui contient le concert
        schedule = self._schedules.get_by_concert_id(command.concert_id)
        if schedule is None:
            raise ConcertNotFoundError(command.concert_id)
        concert = schedule.get_concert(command.concert_id)

        # R3 s'applique aussi entre festivals : un artiste est global.
        bookings_elsewhere = [
            booking
            for booking in self._concerts.list_for_artist(concert.artist_id)
            if booking.festival_id != schedule.festival_id
        ]

        # 3. Mutation métier : le planning vérifie ses règles, puis produit l'événement ConcertRescheduled
        event = schedule.reschedule_concert(command.concert_id, new_slot, bookings_elsewhere)

        # 4. Persistance (validée avant tout effet secondaire)
        self._schedules.save(schedule)

        # 5. Effet secondaire : la notification réagit à l'événement.
        #    Un échec est journalisé et signalé dans le résultat, sans annuler le déplacement (Défaut 2).
        try:
            self._notification_sender.notify_concert_rescheduled(event)
        except Exception as exc:  # noqa: BLE001 - toute panne du canal de notification est non bloquante
            logger.warning(
                "Échec de l'envoi de notification pour le concert #%s : %s",
                concert.id,
                exc,
            )
            return RescheduleConcertResult(concert=concert, notification_sent=False, notification_error=str(exc))

        return RescheduleConcertResult(concert=concert, notification_sent=True)
