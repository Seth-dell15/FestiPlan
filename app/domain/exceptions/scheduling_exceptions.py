class DomainException(Exception):
    """Exception de base pour toutes les erreurs métier du domaine."""
    pass


class SchedulingConflictError(DomainException):
    """L'opération est incompatible avec l'état actuel du planning (HTTP 409)."""


class SchedulingNotFoundError(DomainException):
    """Une ressource référencée par la programmation est introuvable (HTTP 404)."""


class InvalidTimeSlotError(DomainException):
    """R1 : L'heure de fin d'un concert doit être strictement postérieure à son heure de début."""
    def __init__(self, message: str = "La date de fin doit être strictement postérieure à la date de début"):
        super().__init__(message)


class StageOccupiedError(SchedulingConflictError):
    """R2 : Deux concerts ne peuvent pas se chevaucher sur une même scène."""
    def __init__(self, message: str = "Conflit : la scène est déjà occupée sur ce créneau"):
        super().__init__(message)


class ArtistAlreadyBookedError(SchedulingConflictError):
    """R3 : Un artiste ne peut pas jouer dans deux concerts qui se chevauchent."""
    def __init__(self, message: str = "Conflit : l'artiste est déjà programmé sur ce créneau"):
        super().__init__(message)


class ConcertOutsideFestivalError(DomainException):
    """R6 : Un concert doit se dérouler entièrement dans la période du festival."""
    def __init__(self, message: str = "Le concert doit se dérouler entièrement pendant la période du festival"):
        super().__init__(message)


class CannotModifyPublishedFestivalError(SchedulingConflictError):
    """R7 : Un planning publié ne doit pas pouvoir être modifié par une opération ordinaire."""
    def __init__(self, message: str = "Impossible de modifier la programmation d'un festival déjà publié"):
        super().__init__(message)


class ConcertNotFoundError(SchedulingNotFoundError):
    """Le concert demandé n'existe pas."""
    def __init__(self, concert_id: int):
        super().__init__(f"Concert avec l'identifiant {concert_id} introuvable")
        self.concert_id = concert_id


# --- Ajouts Dev 1 : catégories d'erreurs utilisées par l'adaptateur HTTP -------------

class UnknownFestivalError(SchedulingNotFoundError):
    """R4 : le festival référencé par le concert n'existe pas."""
    def __init__(self, festival_id: int):
        super().__init__(f"Festival avec l'identifiant {festival_id} introuvable")
        self.festival_id = festival_id


class UnknownArtistError(SchedulingNotFoundError):
    """R4 : l'artiste référencé par le concert n'existe pas."""
    def __init__(self, artist_id: int):
        super().__init__(f"Artiste avec l'identifiant {artist_id} introuvable")
        self.artist_id = artist_id


class UnknownStageError(SchedulingNotFoundError):
    """R4 : la scène référencée par le concert n'existe pas."""
    def __init__(self, stage_id: int):
        super().__init__(f"Scène avec l'identifiant {stage_id} introuvable")
        self.stage_id = stage_id


class StageNotInFestivalError(DomainException):
    """R4 : la scène doit appartenir au festival du concert."""
    def __init__(self, stage_id: int, festival_id: int):
        super().__init__(f"La scène #{stage_id} n'appartient pas au festival #{festival_id}")


class MissingStageEquipmentError(DomainException):
    """R5 : les équipements requis par l'artiste doivent être disponibles sur la scène."""
    def __init__(self, stage_name: str, missing: frozenset[str]):
        super().__init__(
            f"La scène {stage_name} ne dispose pas des équipements requis : {', '.join(sorted(missing))}"
        )
        self.missing = missing


class ConcertAlreadyCancelledError(SchedulingConflictError, ValueError):
    """Un concert annulé ne peut être ni déplacé ni annulé à nouveau.

    Hérite aussi de ValueError pour rester compatible avec le code existant.
    """
    def __init__(self, message: str = "Impossible de déplacer un concert annulé"):
        super().__init__(message)
