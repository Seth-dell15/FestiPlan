from typing import Protocol

from app.domain.events.concert_events import ConcertRescheduledEvent
from app.domain.events.operation_events import FestivalPublishedEvent


class INotificationSenderPort(Protocol):
    """Port sortant : réagit aux événements de domaine, une fois le fait métier enregistré."""

    def notify_concert_rescheduled(self, event: ConcertRescheduledEvent) -> None:
        ...

    def notify_festival_published(self, event: FestivalPublishedEvent) -> None:
        ...
