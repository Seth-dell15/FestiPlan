from app.domain.models.concert import Concert
from app.domain.ports.repositories.concert_query_port import IConcertQueryPort
from app.domain.exceptions.scheduling_exceptions import ConcertNotFoundError


class GetConcertUseCase:
    """Cas d'usage : Consulter un concert par son identifiant."""

    def __init__(self, concert_repository: IConcertQueryPort):
        self._concert_repo = concert_repository

    def execute(self, concert_id: int) -> Concert:
        concert = self._concert_repo.get_by_id(concert_id)
        if concert is None:
            raise ConcertNotFoundError(concert_id)
        return concert
