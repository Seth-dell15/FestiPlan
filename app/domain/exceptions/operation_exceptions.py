class DomainException(Exception):
    """Exception de base du domaine."""
    pass


class IncidentInvalidDescriptionError(DomainException):
    """Levée lorsque la description de l'incident est vide ou invalide (R10)."""
    pass


class IncidentNotFoundError(DomainException):
    """Levée lorsqu'un incident demandé n'existe pas."""
    pass


class IncidentAlreadyResolvedError(DomainException):
    """Levée lorsqu'on tente de résoudre un incident déjà résolu."""
    pass


class FestivalNotFoundError(DomainException):
    """Levée lorsqu'un festival est introuvable."""
    pass


class FestivalAlreadyPublishedError(DomainException):
    """Levée lorsqu'on tente de publier un festival déjà publié."""
    pass


class CannotPublishInvalidScheduleError(DomainException):
    """Levée lorsqu'on tente de publier un planning contenant des conflits ou non conforme (R8)."""
    pass
