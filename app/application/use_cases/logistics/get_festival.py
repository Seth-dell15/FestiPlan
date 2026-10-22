from app.domain.exceptions.logistics_exceptions import FestivalNotFoundError
from app.domain.models.festival import Festival
from app.domain.ports.repositories.festival_repository_port import FestivalRepositoryPort


class GetFestivalUseCase:
    def __init__(self, festival_repository: FestivalRepositoryPort):
        self._festivals = festival_repository

    def execute(self, festival_id: int) -> Festival:
        festival = self._festivals.get(festival_id)
        if festival is None:
            raise FestivalNotFoundError(festival_id)
        return festival
