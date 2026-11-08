from app.schemas import ConcertRead


class ConcertRescheduleRead(ConcertRead):
    """Réponse du déplacement : le concert déplacé + l'état de la notification (Défaut 2).

    Le déplacement est enregistré même si notification_sent vaut False.
    """
    notification_sent: bool
