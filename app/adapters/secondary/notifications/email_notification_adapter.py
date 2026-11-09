from app.domain.ports.services.notification_sender_port import INotificationSenderPort
from app.utils.email_sender import send_email


class EmailNotificationAdapter(INotificationSenderPort):
    """Adaptateur secondaire branché sur le service d'envoi d'email de notification."""

    def __init__(self, recipient: str = "production@festiplan.test"):
        self.recipient = recipient

    def notify_schedule_change(self, concert_id: int, message: str) -> None:
        send_email(
            recipient=self.recipient,
            subject=f"Modification du concert #{concert_id}",
            body=message,
        )
