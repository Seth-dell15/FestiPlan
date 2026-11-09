import logging

from app.application.ports.inbound import IPublishFestivalPort, PublishFestivalResult
from app.domain.models.festival import Festival
from app.domain.services import scheduling_policy as policy
from app.domain.ports.repositories.artist_repository_port import IArtistRepository
from app.domain.ports.repositories.concert_repository_port import IConcertRepository
from app.domain.ports.repositories.festival_repository_port import IFestivalRepository
from app.domain.ports.repositories.stage_repository_port import IStageRepository
from app.domain.ports.services.notification_sender_port import INotificationSenderPort
from app.domain.exceptions.logistics_exceptions import FestivalNotFoundError

logger = logging.getLogger(__name__)


class PublishFestivalUseCase(IPublishFestivalPort):
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
        stages = {concert.stage_id: self._stages.get_by_id(concert.stage_id) for concert in concerts}
        artists = {concert.artist_id: self._artists.get_by_id(concert.artist_id) for concert in concerts}
        bookings_elsewhere = [
            booking
            for artist_id in artists
            for booking in self._concerts.list_for_artist(artist_id)
            if booking.festival_id != festival.id
        ]
        policy.ensure_publishable(festival, concerts, stages, artists, bookings_elsewhere)
