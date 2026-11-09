from app.domain.models.concert import Concert
from app.domain.services import scheduling_policy as policy
from app.domain.ports.repositories.concert_repository_port import IConcertRepository
from app.domain.ports.repositories.festival_repository_port import IFestivalQueryPort
from app.domain.exceptions.scheduling_exceptions import ConcertNotFoundError, UnknownFestivalError


class CancelConcertUseCase:
    """Cas d'usage : Annuler un concert existant.

    - R7 : refusé si le planning du festival est publié (l'annulation modifie le planning).
    - Un concert déjà annulé ne peut pas l'être une seconde fois (garanti par Concert.cancel).
    """

    def __init__(self, concert_repository: IConcertRepository, festival_query_port: IFestivalQueryPort):
        self._concert_repo = concert_repository
        self._festival_port = festival_query_port

    def execute(self, concert_id: int) -> Concert:
        concert = self._concert_repo.get_by_id(concert_id)
        if concert is None:
            raise ConcertNotFoundError(concert_id)

        festival = self._festival_port.get_schedule_info(concert.festival_id)
        if festival is None:
            raise UnknownFestivalError(concert.festival_id)
        policy.ensure_festival_is_modifiable(festival)

        concert.cancel()
        return self._concert_repo.save(concert)
