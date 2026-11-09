from app.domain.models.concert import Concert
from app.domain.ports.repositories.concert_repository_port import IConcertRepository


class GetFestivalScheduleUseCase:
    """Cas d'usage : Consulter le planning des concerts d'un festival dans l'ordre chronologique."""

    def __init__(self, concert_repository: IConcertRepository):
        self._concert_repo = concert_repository

    def execute(self, festival_id: int, include_cancelled: bool = False) -> list[Concert]:
        return self._concert_repo.list_for_festival(
            festival_id=festival_id,
            include_cancelled=include_cancelled,
        )
