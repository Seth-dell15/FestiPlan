from app.domain.models.festival import Festival
from app.domain.ports.repositories.festival_repository_port import FestivalRepositoryPort


class ListFestivalsUseCase:
    def __init__(self, festival_repository: FestivalRepositoryPort):
        self._festivals = festival_repository

    def execute(self) -> list[Festival]:
        return self._festivals.list()
