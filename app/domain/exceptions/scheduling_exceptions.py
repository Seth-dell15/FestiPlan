class DomainException(Exception):
    """Exception de base pour toutes les erreurs métier du domaine."""
    pass


class InvalidTimeSlotError(DomainException):
    """R1 : L'heure de fin d'un concert doit être strictement postérieure à son heure de début."""
    def __init__(self, message: str = "La date de fin doit être strictement postérieure à la date de début"):
        super().__init__(message)


class StageOccupiedError(DomainException):
    """R2 : Deux concerts ne peuvent pas se chevaucher sur une même scène."""
    def __init__(self, message: str = "Conflit : la scène est déjà occupée sur ce créneau"):
        super().__init__(message)


class ArtistAlreadyBookedError(DomainException):
    """R3 : Un artiste ne peut pas jouer dans deux concerts qui se chevauchent."""
    def __init__(self, message: str = "Conflit : l'artiste est déjà programmé sur ce créneau"):
        super().__init__(message)


class ConcertOutsideFestivalError(DomainException):
    """R6 : Un concert doit se dérouler entièrement dans la période du festival."""
    def __init__(self, message: str = "Le concert doit se dérouler entièrement pendant la période du festival"):
        super().__init__(message)


class CannotModifyPublishedFestivalError(DomainException):
    """R7 : Un planning publié ne doit pas pouvoir être modifié par une opération ordinaire."""
    def __init__(self, message: str = "Impossible de modifier la programmation d'un festival déjà publié"):
        super().__init__(message)


class ConcertNotFoundError(DomainException):
    """Le concert demandé n'existe pas."""
    def __init__(self, concert_id: int):
        super().__init__(f"Concert avec l'identifiant {concert_id} introuvable")
        self.concert_id = concert_id
