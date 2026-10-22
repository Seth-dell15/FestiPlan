from dataclasses import dataclass
from datetime import datetime
import logging
from app.domain.models.concert import Concert
from app.domain.value_objects.time_slot import TimeSlot
from app.domain.ports.repositories.concert_repository_port import IConcertRepository
from app.domain.ports.repositories.festival_repository_port import IFestivalQueryPort
from app.domain.ports.services.notification_sender_port import INotificationSenderPort
from app.domain.exceptions.scheduling_exceptions import (
    ConcertNotFoundError,
    ConcertOutsideFestivalError,
    CannotModifyPublishedFestivalError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RescheduleConcertCommand:
    """Commande applicative pour déplacer un concert."""
    concert_id: int
    new_start: datetime
    new_end: datetime


@dataclass(frozen=True)
class RescheduleConcertResult:
    """Résultat du cas d'usage de déplacement.
    
    Permet de distinguer clairement la réussite de l'opération métier
    du statut de l'effet secondaire (notification).
    """
    concert: Concert
    notification_sent: bool
    notification_error: str | None = None


class RescheduleConcertUseCase:
    """Cas d'usage : Déplacer un concert.
    
    Corrige les défauts majeurs identifiés dans le legacy :
    - R1 : fin > début (garanti par TimeSlot)
    - R2 : Pas de chevauchement sur la même scène
    - R3 : Pas de chevauchement pour le même artiste
    - R6 : Respect des dates du festival
    - R7 : Protection si le planning du festival est déjà publié
    - Défaut 2 : Découplage de la notification (l'échec d'envoi ne corrompt pas la persistance)
    """

    def __init__(
        self,
        concert_repository: IConcertRepository,
        festival_query_port: IFestivalQueryPort | None = None,
        notification_sender: INotificationSenderPort | None = None,
    ):
        self._concert_repo = concert_repository
        self._festival_port = festival_query_port
        self._notification_sender = notification_sender

    def execute(self, command: RescheduleConcertCommand) -> RescheduleConcertResult:
        # 1. Récupération du concert
        concert = self._concert_repo.get_by_id(command.concert_id)
        if concert is None:
            raise ConcertNotFoundError(command.concert_id)

        # 2. Création du nouveau créneau (vérifie R1)
        new_slot = TimeSlot(start=command.new_start, end=command.new_end)

        # 3. Vérification des contraintes du festival (R6 et R7)
        if self._festival_port is not None:
            festival_info = self._festival_port.get_schedule_info(concert.festival_id)
            if festival_info is not None:
                # R7 : Le planning publié ne peut pas être modifié par une opération ordinaire
                if festival_info.is_published:
                    raise CannotModifyPublishedFestivalError(
                        f"Le festival #{concert.festival_id} a déjà été publié. "
                        "Les modifications ordinaires du planning sont verrouillées."
                    )
                # R6 : Le concert doit se dérouler entièrement pendant la période du festival
                if not new_slot.is_within(festival_info.start_date, festival_info.end_date):
                    raise ConcertOutsideFestivalError(
                        f"Le créneau ({new_slot.start} - {new_slot.end}) dépasse "
                        f"les dates du festival ({festival_info.start_date} - {festival_info.end_date})"
                    )

        # 4. Vérification des conflits (R2 et R3)
        # Création d'une version candidate du concert avec le nouveau créneau
        candidate_concert = Concert(
            id=concert.id,
            festival_id=concert.festival_id,
            artist_id=concert.artist_id,
            stage_id=concert.stage_id,
            time_slot=new_slot,
            status=concert.status,
        )

        existing_concerts = self._concert_repo.list_for_festival(
            festival_id=concert.festival_id,
            include_cancelled=False,
        )

        for other in existing_concerts:
            candidate_concert.check_conflict_with(other)

        # 5. Application de la mutation métier
        concert.reschedule(new_slot)

        # 6. Persistance
        persisted_concert = self._concert_repo.save(concert)

        # 7. Effet secondaire : notification isolée (Défaut 2 corrigé)
        notification_sent = False
        notification_error = None

        if self._notification_sender is not None:
            try:
                self._notification_sender.notify_schedule_change(
                    concert_id=persisted_concert.id or command.concert_id,
                    message=f"Le concert a été déplacé au {new_slot.start.isoformat()}",
                )
                notification_sent = True
            except Exception as exc:
                notification_error = str(exc)
                logger.warning(
                    "Échec de l'envoi de notification pour le concert #%s : %s",
                    persisted_concert.id,
                    exc,
                )

        return RescheduleConcertResult(
            concert=persisted_concert,
            notification_sent=notification_sent,
            notification_error=notification_error,
        )
