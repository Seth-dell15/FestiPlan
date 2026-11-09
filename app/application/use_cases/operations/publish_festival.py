import logging
from dataclasses import dataclass

from app.domain.models.concert import Concert
from app.domain.models.festival import Festival
from app.domain.services import scheduling_policy as policy
from app.domain.ports.repositories.artist_repository_port import IArtistRepository
from app.domain.ports.repositories.concert_repository_port import IConcertRepository
from app.domain.ports.repositories.festival_repository_port import IFestivalRepository
from app.domain.ports.repositories.stage_repository_port import IStageRepository
from app.domain.ports.services.notification_sender_port import INotificationSenderPort
from app.domain.exceptions.logistics_exceptions import EquipmentMismatchError, FestivalNotFoundError
from app.domain.exceptions.operation_exceptions import CannotPublishInvalidScheduleError
from app.domain.exceptions.scheduling_exceptions import (
    ArtistAlreadyBookedError,
    StageNotInFestivalError,
    StageOccupiedError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PublishFestivalResult:
    festival: Festival
    notification_sent: bool


class PublishFestivalUseCase:
    """Cas d'usage : Publication officielle du planning d'un festival.

    Invariants et règles garantis :
    - R8 : Le planning ne peut être publié que si ses concerts respectent les règles de
      programmation (références R4, équipements R5, dates R6, conflits R2 et R3).
    - La transition PREPARATION -> PUBLISHED est portée par l'entité Festival.
    - Défaut 2 : L'échec éventuel de la notification est capté et non bloquant.
    """

    def __init__(
        self,
        festival_repository: IFestivalRepository,
        concert_repository: IConcertRepository,
        stage_repository: IStageRepository,
        artist_repository: IArtistRepository,
        notification_sender: INotificationSenderPort,
    ) -> None:
        self._festivals = festival_repository
        self._concerts = concert_repository
        self._stages = stage_repository
        self._artists = artist_repository
        self._notification_sender = notification_sender

    def execute(self, festival_id: int) -> PublishFestivalResult:
        festival = self._festivals.get_by_id(festival_id)
        if festival is None:
            raise FestivalNotFoundError(festival_id)

        # Le planning est vérifié avant la transition, pour ne jamais marquer publié un festival refusé.
        self._ensure_schedule_is_valid(festival)
        event = festival.publish()
        published = self._festivals.save(festival)

        # La notification réagit à l'événement ; un échec est journalisé sans annuler la publication (Défaut 2).
        try:
            self._notification_sender.notify_festival_published(event)
        except Exception as exc:  # noqa: BLE001 - toute panne du canal de notification est non bloquante
            logger.warning(
                "Échec de l'envoi de notification de publication pour le festival #%s : %s",
                festival_id,
                exc,
            )
            return PublishFestivalResult(festival=published, notification_sent=False)

        return PublishFestivalResult(festival=published, notification_sent=True)

    def _ensure_schedule_is_valid(self, festival: Festival) -> None:
        concerts = self._concerts.list_for_festival(festival.id, include_cancelled=False)
        if not concerts:
            raise CannotPublishInvalidScheduleError("Impossible de publier un planning sans concert programmé.")
        for index, concert in enumerate(concerts):
            if not concert.time_slot.is_within(festival.period.start, festival.period.end):
                raise CannotPublishInvalidScheduleError(
                    f"Impossible de publier le planning : le concert #{concert.id} déborde des dates du festival (R6)."
                )
            self._ensure_concert_fits_its_stage(festival, concert)
            for other in concerts[index + 1:]:
                try:
                    concert.check_conflict_with(other)
                except (StageOccupiedError, ArtistAlreadyBookedError) as conflict:
                    raise CannotPublishInvalidScheduleError(
                        f"Impossible de publier le planning : conflit de programmation détecté ({conflict}) (R8)."
                    ) from conflict

    def _ensure_concert_fits_its_stage(self, festival: Festival, concert: Concert) -> None:
        stage = self._stages.get_by_id(concert.stage_id)
        artist = self._artists.get_by_id(concert.artist_id)
        if stage is None or artist is None:
            raise CannotPublishInvalidScheduleError(
                f"Impossible de publier le planning : le concert #{concert.id} référence une scène ou un artiste inconnu (R4)."
            )
        try:
            policy.ensure_stage_can_host(festival.id, stage, artist)
        except (StageNotInFestivalError, EquipmentMismatchError) as exc:
            raise CannotPublishInvalidScheduleError(
                f"Impossible de publier le planning : concert #{concert.id} invalide ({exc}) (R4/R5)."
            ) from exc
