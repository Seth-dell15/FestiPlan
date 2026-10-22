from typing import Protocol


class INotificationSenderPort(Protocol):
    """Port sortant pour la transmission d'alertes et de notifications aux équipes ou festivaliers."""

    def notify_schedule_change(self, concert_id: int, message: str) -> None:
        """Envoie une notification suite à un changement de programmation."""
        ...
