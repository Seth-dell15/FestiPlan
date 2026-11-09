import logging
from app.application.ports.inbound import (
    IRescheduleConcertPort,
    RescheduleConcertCommand,
    RescheduleConcertResult,
)
from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.services import scheduling_policy as policy
from app.domain.ports.repositories.concert_repository_port import IConcertRepository
from app.domain.ports.repositories.festival_repository_port import IFestivalQueryPort
from app.domain.ports.services.notification_sender_port import INotificationSenderPort
from app.domain.exceptions.scheduling_exceptions import (
    ConcertAlreadyCancelledError,
    ConcertNotFoundError,
    UnknownFestivalError,
)

logger = logging.getLogger(__name__)


class RescheduleConcertUseCase(IRescheduleConcertPort):
    """Cas d'usage : Déplacer un concert.

    Corrige le Défaut 1 en réappliquant les mêmes règles que la programmation
    (via scheduling_policy), puis isole la notification (Défaut 2) :
    - Concert annulé : refusé (ConcertAlreadyCancelledError)
    - R1 : fin > début (garanti par TimeSlot)
    - R7 : planning publié verrouillé
    - R6 : respect des dates du festival
    - R2 / R3 : pas de chevauchement de scène ni d'artiste (le concert lui-même est ignoré)
    La scène et l'artiste ne changent pas lors d'un déplacement : R4 et R5 restent donc
    satisfaites et ne sont pas re-vérifiées ici.
    """

    def __init__(
        self,
        concert_repository: IConcertRepository,
        festival_query_port: IFestivalQueryPort,
        notification_sender: INotificationSenderPort,
    ):
        self._concert_repo = concert_repository
        self._festival_port = festival_query_port
        self._notification_sender = notification_sender

    def execute(self, command: RescheduleConcertCommand) -> RescheduleConcertResult:
        # 1. Récupération du concert
        concert = self._concert_repo.get_by_id(command.concert_id)
        if concert is None:
            raise ConcertNotFoundError(command.concert_id)
        if concert.is_cancelled:
            raise ConcertAlreadyCancelledError("Impossible de déplacer un concert annulé")

        # 2. Création du nouveau créneau (vérifie R1)
        new_slot = TimeSlot(start=command.new_start, end=command.new_end)

        # 3. Contraintes du festival (R7 puis R6)
        festival = self._festival_port.get_schedule_info(concert.festival_id)
        if festival is None:
            raise UnknownFestivalError(concert.festival_id)
        policy.ensure_festival_is_modifiable(festival)
        policy.ensure_within_festival(new_slot, festival)

        # 4. Conflits (R2 et R3) sur une version candidate, avant toute mutation
        candidate = Concert(
            id=concert.id,
            festival_id=concert.festival_id,
            artist_id=concert.artist_id,
            stage_id=concert.stage_id,
            time_slot=new_slot,
            status=concert.status,
        )
        # R3 s'applique aussi entre festivals : un artiste est global.
        policy.ensure_no_conflict(
            candidate,
            [
                *self._concert_repo.list_for_festival(festival_id=concert.festival_id, include_cancelled=False),
                *self._concert_repo.list_for_artist(concert.artist_id),
            ],
        )

        # 5. Mutation métier : l'entité produit l'événement ConcertRescheduled
        event = concert.reschedule(new_slot)

        # 6. Persistance (validée avant tout effet secondaire)
        persisted_concert = self._concert_repo.save(concert)

        # 7. Effet secondaire : la notification réagit à l'événement.
        #    Un échec est journalisé et signalé dans le résultat, sans annuler le déplacement (Défaut 2).
        try:
            self._notification_sender.notify_concert_rescheduled(event)
        except Exception as exc:  # noqa: BLE001 - toute panne du canal de notification est non bloquante
            logger.warning(
                "Échec de l'envoi de notification pour le concert #%s : %s",
                persisted_concert.id,
                exc,
            )
            return RescheduleConcertResult(
                concert=persisted_concert, notification_sent=False, notification_error=str(exc)
            )

        return RescheduleConcertResult(concert=persisted_concert, notification_sent=True)
