from app.domain.models.concert import Concert
from app.domain.ports.repositories.schedule_repository_port import IScheduleRepository
from app.domain.exceptions.scheduling_exceptions import ConcertNotFoundError


class CancelConcertUseCase:
    """Cas d'usage : Annuler un concert existant.

    L'annulation passe par le planning :
    - R7 : refusée si le planning du festival est publié (elle modifie le planning).
    - Un concert déjà annulé ne peut pas l'être une seconde fois (garanti par Concert.cancel).
    """

    def __init__(self, schedule_repository: IScheduleRepository):
        self._schedules = schedule_repository

    def execute(self, concert_id: int) -> Concert:
        schedule = self._schedules.get_by_concert_id(concert_id)
        if schedule is None:
            raise ConcertNotFoundError(concert_id)

        concert = schedule.cancel_concert(concert_id)
        self._schedules.save(schedule)
        return concert
