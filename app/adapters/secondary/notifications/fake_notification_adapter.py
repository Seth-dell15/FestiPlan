from app.domain.ports.services.notification_sender_port import INotificationSenderPort


class FakeNotificationAdapter(INotificationSenderPort):
    """Adaptateur de notification factice pour enregistrer les appels ou simuler une panne."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.sent_notifications: list[dict[str, str | int]] = []

    def notify_schedule_change(self, concert_id: int, message: str) -> None:
        if self.should_fail:
            raise RuntimeError("Simulation d'échec du service de notification")
        self.sent_notifications.append({"concert_id": concert_id, "message": message})
