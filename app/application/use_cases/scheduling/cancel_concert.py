from app.domain.models.concert import Concert
from app.domain.ports.repositories.concert_repository_port import IConcertRepository
from app.domain.exceptions.scheduling_exceptions import ConcertNotFoundError


class CancelConcertUseCase:
    """Cas d'usage : Annuler un concert existant."""

    def __init__(self, concert_repository: IConcertRepository):
        self._concert_repo = concert_repository

    def execute(self, concert_id: int) -> Concert:
        concert = self._concert_repo.get_by_id(concert_id)
        if concert is None:
            raise ConcertNotFoundError(concert_id)

        concert.cancel()
        return self._concert_repo.save(concert)
