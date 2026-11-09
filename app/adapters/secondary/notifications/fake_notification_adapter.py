from app.domain.events.concert_events import ConcertRescheduledEvent
from app.domain.events.operation_events import FestivalPublishedEvent
from app.domain.ports.services.notification_sender_port import INotificationSenderPort


class FakeNotificationAdapter(INotificationSenderPort):
    """Adaptateur de notification factice pour enregistrer les événements ou simuler une panne."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.sent_notifications: list[ConcertRescheduledEvent | FestivalPublishedEvent] = []

    def notify_concert_rescheduled(self, event: ConcertRescheduledEvent) -> None:
        self._record(event)

    def notify_festival_published(self, event: FestivalPublishedEvent) -> None:
        self._record(event)

    def _record(self, event: ConcertRescheduledEvent | FestivalPublishedEvent) -> None:
        if self.should_fail:
            raise RuntimeError("Simulation d'échec du service de notification")
        self.sent_notifications.append(event)
