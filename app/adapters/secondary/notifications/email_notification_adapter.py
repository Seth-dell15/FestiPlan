from app.domain.events.concert_events import ConcertRescheduledEvent
from app.domain.events.operation_events import FestivalPublishedEvent
from app.domain.ports.services.notification_sender_port import INotificationSenderPort
from app.utils.email_sender import send_email


class EmailNotificationAdapter(INotificationSenderPort):
    """Traduit les événements de domaine en emails."""

    def __init__(self, recipient: str = "production@festiplan.test"):
        self.recipient = recipient

    def notify_concert_rescheduled(self, event: ConcertRescheduledEvent) -> None:
        send_email(
            recipient=self.recipient,
            subject=f"Modification du concert #{event.concert_id}",
            body=(
                f"Le concert a été déplacé du {event.previous_time_slot.start.isoformat()} "
                f"au {event.new_time_slot.start.isoformat()}"
            ),
        )

    def notify_festival_published(self, event: FestivalPublishedEvent) -> None:
        send_email(
            recipient=self.recipient,
            subject=f"Publication du festival #{event.festival_id}",
            body=f"Le planning officiel du festival '{event.festival_name}' est maintenant publié !",
        )
