class LogisticsError(ValueError):
    """Erreur métier du référentiel (festivals, scènes, artistes).

    Hérite de ValueError pour rester compatible avec les routes actuelles, qui traduisent ValueError en HTTP 400.
    """


class InvalidFestivalDatesError(LogisticsError):
    pass


class InvalidCapacityError(LogisticsError):
    pass


class EquipmentMismatchError(LogisticsError):
    pass


class FestivalNotFoundError(LogisticsError):
    def __init__(self, festival_id: int):
        super().__init__(f"Festival {festival_id} introuvable")
        self.festival_id = festival_id
