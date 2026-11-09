from app.domain.exceptions.scheduling_exceptions import DomainException


class InvalidFestivalDatesError(DomainException):
    pass


class InvalidCapacityError(DomainException):
    pass


class EquipmentMismatchError(DomainException):
    pass


class FestivalNotFoundError(DomainException):
    def __init__(self, festival_id: int):
        super().__init__(f"Festival {festival_id} introuvable")
        self.festival_id = festival_id
