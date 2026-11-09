import logging

from app.application.ports.inbound import IUnpublishFestivalPort, UnpublishFestivalResult
from app.domain.exceptions.logistics_exceptions import FestivalNotFoundError
from app.domain.ports.repositories.festival_repository_port import IFestivalRepository
from app.domain.ports.services.notification_sender_port import INotificationSenderPort

logger = logging.getLogger(__name__)


class UnpublishFestivalUseCase(IUnpublishFestivalPort):
    """Cas d'usage : retirer un planning publié pour pouvoir le modifier (procédure explicite de R7)."""

    def __init__(
        self,
        festival_repository: IFestivalRepository,
        notification_sender: INotificationSenderPort,
    ) -> None:
        self._festivals = festival_repository
        self._notification_sender = notification_sender

    def execute(self, festival_id: int) -> UnpublishFestivalResult:
        festival = self._festivals.get_by_id(festival_id)
        if festival is None:
            raise FestivalNotFoundError(festival_id)

        event = festival.unpublish()
        unpublished = self._festivals.save(festival)

        # Un échec de notification est journalisé sans annuler le retrait (Défaut 2).
        try:
            self._notification_sender.notify_festival_unpublished(event)
        except Exception as exc:  # noqa: BLE001 - toute panne du canal de notification est non bloquante
            logger.warning(
                "Échec de l'envoi de notification de retrait pour le festival #%s : %s",
                festival_id,
                exc,
            )
            return UnpublishFestivalResult(festival=unpublished, notification_sent=False)

        return UnpublishFestivalResult(festival=unpublished, notification_sent=True)
