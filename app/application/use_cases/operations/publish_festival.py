import logging
from dataclasses import dataclass
from app.domain.ports.repositories.festival_repository_port import (
    IFestivalQueryPort,
    IFestivalCommandPort,
    FestivalScheduleInfo,
)
from app.domain.ports.repositories.concert_repository_port import IConcertRepository
from app.domain.ports.services.notification_sender_port import INotificationSenderPort
from app.domain.exceptions.operation_exceptions import (
    FestivalNotFoundError,
    FestivalAlreadyPublishedError,
    CannotPublishInvalidScheduleError,
)
from app.domain.exceptions.scheduling_exceptions import (
    StageOccupiedError,
    ArtistAlreadyBookedError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PublishFestivalResult:
    festival: FestivalScheduleInfo
    notification_sent: bool


class PublishFestivalUseCase:
    """Cas d'usage : Publication officielle du planning d'un festival.
    
    Invariants et règles garantis :
    - R8 : Le planning ne peut être publié que si ses concerts respectent strictement
      toutes les règles de programmation (non-chevauchement R2, disponibilité artiste R3,
      dates du festival R6).
    - Défaut 2 : L'échec éventuel de la notification est capté et non bloquant.
    """

    def __init__(
        self,
        festival_query: IFestivalQueryPort,
        festival_cmd: IFestivalCommandPort,
        concert_repo: IConcertRepository,
        notification_sender: INotificationSenderPort,
    ) -> None:
        self.festival_query = festival_query
        self.festival_cmd = festival_cmd
        self.concert_repo = concert_repo
        self.notification_sender = notification_sender

    def execute(self, festival_id: int) -> PublishFestivalResult:
        # 1. Vérifier que le festival existe
        fest_info = self.festival_query.get_schedule_info(festival_id)
        if fest_info is None:
            raise FestivalNotFoundError(f"Festival #{festival_id} introuvable.")

        # 2. Vérifier qu'il n'est pas déjà publié
        if fest_info.is_published:
            raise FestivalAlreadyPublishedError(
                f"Le festival '{fest_info.name}' est déjà publié."
            )

        # 3. Contrôle de cohérence du planning (Règle R8)
        active_concerts = self.concert_repo.list_for_festival(
            festival_id, include_cancelled=False
        )

        for i in range(len(active_concerts)):
            c1 = active_concerts[i]
            # Vérifier R6 : dans les dates du festival
            if not c1.time_slot.is_within(fest_info.start_date, fest_info.end_date):
                raise CannotPublishInvalidScheduleError(
                    f"Impossible de publier le planning : le concert #{c1.id} déborde des dates du festival (R6)."
                )
            # Vérifier R2 & R3 : pas de conflits entre concerts actifs
            for j in range(i + 1, len(active_concerts)):
                c2 = active_concerts[j]
                try:
                    c1.check_conflict_with(c2)
                except (StageOccupiedError, ArtistAlreadyBookedError) as conflict:
                    raise CannotPublishInvalidScheduleError(
                        f"Impossible de publier le planning : conflit de programmation détecté ({conflict}) (R8)."
                    )

        # 4. Enregistrement de la publication via le port de commande
        updated_festival = self.festival_cmd.publish_festival(festival_id)
        if updated_festival is None:
            raise FestivalNotFoundError(f"Échec de mise à jour du festival #{festival_id}.")

        # 5. Effet secondaire : Notification (non bloquante)
        notification_sent = False
        try:
            notification_sent = self.notification_sender.notify_schedule_change(
                festival_id,
                f"Le planning officiel du festival '{fest_info.name}' est maintenant publié !",
            )
        except Exception as exc:
            logger.warning(
                "Échec de l'envoi de notification de publication pour le festival #%s : %s",
                festival_id,
                exc,
            )

        return PublishFestivalResult(
            festival=updated_festival,
            notification_sent=notification_sent,
        )
